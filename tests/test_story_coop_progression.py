from copy import deepcopy

import pytest

import story_coop_live
from story_content import STORY_EVENTS
from story_coop import build_initial_coop_story_state
from story_coop_combat import COOP_COMBAT_ENDED, CoopCombatError
from story_coop_live import (
    COOP_INTRO_COMBAT_ID,
    COOP_INTRO_ENCOUNTER_ID,
    COOP_LEGACY_CONTENT_VERSION,
    COOP_SECOND_ENCOUNTER_ID,
    COOP_STAGE1_CONTRACT_VERSION,
    advance_coop_after_victory,
    apply_coop_journey_command,
    project_coop_run_for_viewer,
    prepare_coop_stage1_setup,
    start_intro_coop_combat,
    validate_coop_live_state,
)
from story_coop_content import COOP_STORY_CONTENT, compile_coop_story_content


SEED = 'coop-progression-seed'
MEMBERS = [
    {'user_id': 101, 'username': 'coop-one', 'display_name': 'Coop One'},
    {'user_id': 202, 'username': 'coop-two', 'display_name': 'Coop Two'},
]


def _intro_state():
    source = build_initial_coop_story_state(SEED, MEMBERS)
    return start_intro_coop_combat(source, run_seed=SEED)[0]


def _current_initial_map_state():
    source = build_initial_coop_story_state(SEED, MEMBERS)
    setup = prepare_coop_stage1_setup(source)
    opening, _, _ = _journey_action(
        setup,
        101,
        'current-setup-normal-0001',
        'setup_start',
        {'difficulty': 'normal'},
    )
    current = opening
    for seat, user_id in ((0, 101), (1, 202)):
        private = current['room_states_by_player'][str(seat)]
        current, _, _ = _journey_action(
            current,
            user_id,
            f'current-opening-{seat}-0001',
            'opening_choose',
            {'room_id': current['room']['id'], 'option_id': private['options'][0]},
        )
    assert current['phase'] == 'map'
    return current


def _current_first_combat_state():
    current = _current_initial_map_state()
    vote = current['coordination']['map_vote']
    target = vote['option_node_ids'][0]
    for seat, user_id in ((0, 101), (1, 202)):
        current, _, _ = _journey_action(
            current,
            user_id,
            f'current-first-route-{seat}-0001',
            'map_vote',
            {'vote_id': vote['vote_id'], 'node_id': target},
        )
    assert current['phase'] == 'combat'
    return current


def _current_room_state(room_type, *, seat_relics=None):
    current = _current_initial_map_state()
    for seat, relic_ids in (seat_relics or {}).items():
        current['players'][str(seat)]['relics'].extend(relic_ids)
    vote = current['coordination']['map_vote']
    target = vote['option_node_ids'][0]
    for floor in current['map']['floors']:
        for node in floor['nodes']:
            if node['id'] == target:
                node['type'] = room_type
    validate_coop_live_state(current)
    for seat, user_id in ((0, 101), (1, 202)):
        current, _, _ = _journey_action(
            current,
            user_id,
            f'current-{room_type}-route-{seat}-0001',
            'map_vote',
            {'vote_id': vote['vote_id'], 'node_id': target},
        )
    assert current['phase'] == 'room'
    assert current['room']['type'] == room_type
    return current


def _finish_current_combat(state):
    for enemy in state['combat']['enemies']:
        enemy['health'] = 0
    state['combat']['turn'] = COOP_COMBAT_ENDED
    state['combat']['outcome'] = 'victory'
    state['coordination']['combat_ready_seats'] = []
    state['coordination']['combat_ready_round'] = None
    events = advance_coop_after_victory(state, run_seed=SEED)
    validate_coop_live_state(state)
    return state, events


def _journey_action(state, user_id, action_id, action_type, payload):
    return apply_coop_journey_command(
        state,
        authenticated_user_id=user_id,
        action_id=action_id,
        action_type=action_type,
        payload=payload,
        run_seed=SEED,
        expected_sequence=state['coordination']['action_sequence'],
    )


def _reward_state():
    return _finish_current_combat(_intro_state())[0]


def _map_state():
    reward = _reward_state()
    leader_reward = reward['rewards_by_player']['0']
    chosen = leader_reward['options'][0]['card_id']
    after_leader, _, _ = _journey_action(
        reward,
        101,
        'progress-reward-1',
        'reward_choose',
        {'reward_id': leader_reward['reward_id'], 'card_id': chosen},
    )
    member_reward = after_leader['rewards_by_player']['1']
    map_state, _, _ = _journey_action(
        after_leader,
        202,
        'progress-reward-2',
        'reward_choose',
        {'reward_id': member_reward['reward_id'], 'card_id': ''},
    )
    return map_state, chosen


def _resolve_all_rewards(state, prefix, *, choices=None):
    current = state
    choices = choices or {}
    for seat, user_id in ((0, 101), (1, 202)):
        reward = current['rewards_by_player'][str(seat)]
        card_id = choices.get(seat, '')
        current, _, _ = _journey_action(
            current,
            user_id,
            f'{prefix}-{seat}-choice',
            'reward_choose',
            {'reward_id': reward['reward_id'], 'card_id': card_id},
        )
    return current


def _public_run(state, *, status='active', revision=1):
    return {
        'id': 'a' * 32,
        'party_id': 'b' * 32,
        'status': status,
        'schema_version': 10,
        'content_version': state['content_version'],
        'revision': revision,
        'seed': 'must-not-be-public',
        'state': state,
        'created_at': '2026-08-24T00:00:00Z',
        'updated_at': '2026-08-24T00:00:00Z',
        'completed_at': None,
    }


def _advance_to_chest():
    state = _intro_state()
    action_index = 0
    for _ in range(60):
        phase = state['phase']
        if phase == 'combat':
            state, _ = _finish_current_combat(state)
        elif phase == 'reward':
            state = _resolve_all_rewards(state, f'chest-reward-{action_index}')
            action_index += 2
        elif phase == 'map':
            vote = state['coordination']['map_vote']
            selected = vote['option_node_ids'][0]
            for user_id in (101, 202):
                action_index += 1
                state, _, _ = _journey_action(
                    state,
                    user_id,
                    f'chest-route-{action_index}',
                    'map_vote',
                    {'vote_id': vote['vote_id'], 'node_id': selected},
                )
        elif phase == 'room':
            if state['room']['type'] == 'chest':
                return state
            room_id = state['room']['id']
            for user_id in (101, 202):
                action_index += 1
                seat = 0 if user_id == 101 else 1
                options = state['room_states_by_player'][str(seat)]['options']
                choice = 'leave' if 'leave' in options else options[0]
                state, _, _ = _journey_action(
                    state,
                    user_id,
                    f'chest-room-{action_index}',
                    'room_choose',
                    {'room_id': room_id, 'choice': choice},
                )
        else:
            raise AssertionError(f'unexpected phase before chest: {phase}')
    raise AssertionError('controlled map did not reach its fixed chest floor')


def _shop_state():
    map_state, _ = _map_state()
    vote = map_state['coordination']['map_vote']
    node_id = vote['option_node_ids'][0]
    for floor in map_state['map']['floors']:
        for node in floor['nodes']:
            if node['id'] == node_id:
                node['type'] = 'shop'
    validate_coop_live_state(map_state)
    after_first, _, _ = _journey_action(
        map_state,
        101,
        'shop-route-leader',
        'map_vote',
        {'vote_id': vote['vote_id'], 'node_id': node_id},
    )
    shop, _, _ = _journey_action(
        after_first,
        202,
        'shop-route-member',
        'map_vote',
        {'vote_id': vote['vote_id'], 'node_id': node_id},
    )
    return shop


def _event_state():
    map_state, _ = _map_state()
    vote = map_state['coordination']['map_vote']
    node_id = vote['option_node_ids'][0]
    for floor in map_state['map']['floors']:
        for node in floor['nodes']:
            if node['id'] == node_id:
                node['type'] = 'event'
    validate_coop_live_state(map_state)
    after_first, _, _ = _journey_action(
        map_state,
        101,
        'event-route-leader',
        'map_vote',
        {'vote_id': vote['vote_id'], 'node_id': node_id},
    )
    event, _, _ = _journey_action(
        after_first,
        202,
        'event-route-member',
        'map_vote',
        {'vote_id': vote['vote_id'], 'node_id': node_id},
    )
    return event


def _nested_keys(value):
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys.update(_nested_keys(item))
        return keys
    if isinstance(value, list):
        keys = set()
        for item in value:
            keys.update(_nested_keys(item))
        return keys
    return set()


def test_victory_reward_and_personal_choice_are_atomic_and_seat_scoped():
    intro = _intro_state()
    initial_gold = {seat: player['gold'] for seat, player in intro['players'].items()}
    reward, events = _finish_current_combat(intro)

    assert reward['phase'] == 'reward'
    assert reward['combat'] is None
    assert reward['coop_progression']['completed_combat_ids'] == [COOP_INTRO_COMBAT_ID]
    assert reward['last_combat']['encounter_id'] == COOP_INTRO_ENCOUNTER_ID
    assert {event['type'] for event in events} == {'coop_rewards_started'}
    assert all(len(item['options']) == 3 for item in reward['rewards_by_player'].values())
    assert all(reward['players'][seat]['gold'] == initial_gold[seat] + 15 for seat in reward['players'])

    before = deepcopy(reward)
    leader_reward = reward['rewards_by_player']['0']
    chosen = leader_reward['options'][0]['card_id']
    after, choice_events, receipt = _journey_action(
        reward,
        101,
        'progress-personal-choice',
        'reward_choose',
        {'reward_id': leader_reward['reward_id'], 'card_id': chosen},
    )

    assert reward == before
    assert len(after['players']['0']['deck']) == len(before['players']['0']['deck']) + 1
    assert after['players']['0']['deck'][-1]['def_id'] == chosen
    assert after['players']['1']['deck'] == before['players']['1']['deck']
    assert after['phase'] == 'reward'
    assert receipt['actor_seat'] == 0
    assert choice_events[0]['type'] == 'coop_reward_resolved'
    assert 'card_id' not in choice_events[0]


def test_last_reward_starts_vote_and_unanimous_vote_uses_no_tiebreak_rng():
    map_state, chosen = _map_state()
    vote = map_state['coordination']['map_vote']
    node_id = vote['option_node_ids'][0]
    stream = f"coop_route_vote:{vote['vote_id']}"

    assert map_state['phase'] == 'map'
    assert map_state['rewards_by_player'] is None
    assert map_state['shared_reward'] is None
    assert chosen in {card['def_id'] for card in map_state['players']['0']['deck']}
    assert stream not in map_state['rng_streams']

    after_first, _, _ = _journey_action(
        map_state,
        101,
        'progress-unanimous-1',
        'map_vote',
        {'vote_id': vote['vote_id'], 'node_id': node_id},
    )
    second_combat, events, _ = _journey_action(
        after_first,
        202,
        'progress-unanimous-2',
        'map_vote',
        {'vote_id': vote['vote_id'], 'node_id': node_id},
    )

    assert stream not in second_combat['rng_streams']
    assert second_combat['phase'] == 'combat'
    assert second_combat['coop_progression']['encounter_index'] == 2
    assert second_combat['combat']['encounter_id'] == 'garden:simple:001'
    assert second_combat['combat']['id'] == f'garden-route-{node_id}'
    assert [enemy['def_id'] for enemy in second_combat['combat']['enemies']] == [
        'soldier_ant',
    ]
    assert any(event['type'] == 'coop_combat_started' for event in events)


def test_split_vote_consumes_one_named_rng_value_and_second_victory_continues_stage():
    map_state, _ = _map_state()
    vote = map_state['coordination']['map_vote']
    first, second = vote['option_node_ids'][:2]
    stream = f"coop_route_vote:{vote['vote_id']}"

    after_first, _, _ = _journey_action(
        map_state,
        101,
        'progress-split-vote-1',
        'map_vote',
        {'vote_id': vote['vote_id'], 'node_id': first},
    )
    assert stream not in after_first['rng_streams']
    second_combat, _, _ = _journey_action(
        after_first,
        202,
        'progress-split-vote-2',
        'map_vote',
        {'vote_id': vote['vote_id'], 'node_id': second},
    )

    assert second_combat['rng_streams'][stream] == 1
    assert second_combat['current_node_id'] in {first, second}
    reward, events = _finish_current_combat(second_combat)
    assert reward['phase'] == 'reward'
    assert reward['completed'] is False
    assert reward['combat'] is None
    assert reward['coop_progression']['completed_combat_ids'] == [
        COOP_INTRO_COMBAT_ID,
        f"garden-route-{reward['current_node_id']}",
    ]
    assert [event['type'] for event in events] == ['coop_rewards_started']


def test_rest_room_is_personal_private_and_last_choice_returns_to_route_vote():
    first_map, _ = _map_state()
    first_vote = first_map['coordination']['map_vote']
    floor_two = first_vote['option_node_ids'][0]
    after_first, _, _ = _journey_action(
        first_map,
        101,
        'rest-route-first-0',
        'map_vote',
        {'vote_id': first_vote['vote_id'], 'node_id': floor_two},
    )
    second_combat, _, _ = _journey_action(
        after_first,
        202,
        'rest-route-first-1',
        'map_vote',
        {'vote_id': first_vote['vote_id'], 'node_id': floor_two},
    )
    second_reward, _ = _finish_current_combat(second_combat)
    member_card_id = second_reward['rewards_by_player']['1']['options'][0]['card_id']
    second_map = _resolve_all_rewards(
        second_reward,
        'rest-second-reward',
        choices={1: member_card_id},
    )
    second_vote = second_map['coordination']['map_vote']
    rest_node_id = second_vote['option_node_ids'][0]
    for floor in second_map['map']['floors']:
        for node in floor['nodes']:
            if node['id'] == rest_node_id:
                node['type'] = 'rest'
    validate_coop_live_state(second_map)
    after_vote, _, _ = _journey_action(
        second_map,
        101,
        'rest-route-second-0',
        'map_vote',
        {'vote_id': second_vote['vote_id'], 'node_id': rest_node_id},
    )
    rest, events, _ = _journey_action(
        after_vote,
        202,
        'rest-route-second-1',
        'map_vote',
        {'vote_id': second_vote['vote_id'], 'node_id': rest_node_id},
    )
    assert rest['phase'] == 'room'
    assert rest['room']['type'] == 'rest'
    assert any(event['type'] == 'coop_room_started' for event in events)

    member_unique_card = next(
        card
        for card in rest['players']['1']['deck']
        if card['def_id'] == member_card_id
    )
    before_invalid = deepcopy(rest)
    with pytest.raises(CoopCombatError) as invalid_card:
        _journey_action(
            rest,
            101,
            'rest-cross-seat-card',
            'room_choose',
            {
                'room_id': rest['room']['id'],
                'choice': 'upgrade',
                'card_instance_id': member_unique_card['instance_id'],
            },
        )
    assert invalid_card.value.code == 'INVALID_DECK_CARD'
    assert rest == before_invalid

    rest['players']['0']['health'] = 30
    after_heal, heal_events, _ = _journey_action(
        rest,
        101,
        'rest-heal-leader',
        'room_choose',
        {'room_id': rest['room']['id'], 'choice': 'heal'},
    )
    assert after_heal['players']['0']['health'] == 54
    assert after_heal['players']['1']['health'] == rest['players']['1']['health']
    assert heal_events[0]['type'] == 'coop_player_healed'
    assert after_heal['phase'] == 'room'

    leader_view = project_coop_run_for_viewer(_public_run(after_heal), 101)['snapshot']
    member_view = project_coop_run_for_viewer(_public_run(after_heal), 202)['snapshot']
    assert leader_view['room_state']['status'] == 'resolved'
    assert member_view['room_state']['status'] == 'pending'
    assert member_unique_card['instance_id'] not in {
        card['instance_id'] for card in leader_view['room_state']['deck']
    }
    assert member_unique_card['instance_id'] in {
        card['instance_id'] for card in member_view['room_state']['deck']
    }
    assert 'room_states_by_player' not in repr(member_view)

    next_map, upgrade_events, _ = _journey_action(
        after_heal,
        202,
        'rest-upgrade-member',
        'room_choose',
        {
            'room_id': after_heal['room']['id'],
            'choice': 'upgrade',
            'card_instance_id': member_unique_card['instance_id'],
        },
    )
    upgraded = next(
        card
        for card in next_map['players']['1']['deck']
        if card['instance_id'] == member_unique_card['instance_id']
    )
    assert upgraded['upgraded'] is True
    assert next_map['phase'] == 'map'
    assert next_map['room_states_by_player'] is None
    assert next_map['coordination']['room_decision'] is None
    assert rest_node_id in next_map['coop_progression']['completed_node_ids']
    assert {event['type'] for event in upgrade_events} >= {
        'coop_card_upgraded',
        'coop_room_seat_resolved',
        'coop_route_vote_started',
    }


def test_chest_gold_is_deterministic_private_and_claimed_once_per_seat():
    chest = _advance_to_chest()
    repeated = _advance_to_chest()
    amounts = {
        seat: private['gold']
        for seat, private in chest['room_states_by_player'].items()
    }
    assert amounts == {
        seat: private['gold']
        for seat, private in repeated['room_states_by_player'].items()
    }
    assert all(40 <= amount <= 60 for amount in amounts.values())
    room_id = chest['room']['id']
    before_gold = {seat: player['gold'] for seat, player in chest['players'].items()}

    leader_view = project_coop_run_for_viewer(_public_run(chest), 101)['snapshot']
    member_view = project_coop_run_for_viewer(_public_run(chest), 202)['snapshot']
    assert leader_view['room_state']['gold'] == amounts['0']
    assert member_view['room_state']['gold'] == amounts['1']
    assert 'room_states_by_player' not in repr(leader_view)

    after_claim, events, _ = _journey_action(
        chest,
        101,
        'chest-leader-claim',
        'room_choose',
        {'room_id': room_id, 'choice': 'claim_gold'},
    )
    assert after_claim['players']['0']['gold'] == before_gold['0'] + amounts['0']
    assert after_claim['players']['1']['gold'] == before_gold['1']
    assert any(event['type'] == 'coop_chest_gold_claimed' for event in events)
    with pytest.raises(CoopCombatError) as repeated_choice:
        _journey_action(
            after_claim,
            101,
            'chest-leader-repeat',
            'room_choose',
            {'room_id': room_id, 'choice': 'claim_gold'},
        )
    assert repeated_choice.value.code == 'ROOM_ALREADY_RESOLVED'

    next_map, _, _ = _journey_action(
        after_claim,
        202,
        'chest-member-leave',
        'room_choose',
        {'room_id': room_id, 'choice': 'leave'},
    )
    assert next_map['phase'] == 'map'
    assert next_map['players']['1']['gold'] == before_gold['1']


def test_personal_shop_hides_inventory_and_authoritatively_buys_then_leaves():
    shop = _shop_state()
    repeated = _shop_state()
    assert shop['phase'] == 'room'
    assert shop['room']['type'] == 'shop'
    assert shop['room_states_by_player'] == repeated['room_states_by_player']
    leader_private = shop['room_states_by_player']['0']
    member_private = shop['room_states_by_player']['1']
    leader_offer = next(
        offer
        for offer in leader_private['offers']
        if offer['price'] <= shop['players']['0']['gold']
    )
    before = deepcopy(shop)
    bought, events, _ = _journey_action(
        shop,
        101,
        'shop-buy-leader-card',
        'shop_buy',
        {
            'room_id': shop['room']['id'],
            'offer_id': leader_offer['offer_id'],
        },
    )
    assert shop == before
    assert bought['phase'] == 'room'
    assert bought['players']['0']['gold'] == (
        before['players']['0']['gold'] - leader_offer['price']
    )
    assert bought['players']['1'] == before['players']['1']
    purchased = next(
        offer
        for offer in bought['room_states_by_player']['0']['offers']
        if offer['offer_id'] == leader_offer['offer_id']
    )
    assert purchased['status'] == 'purchased'
    assert any(
        card['instance_id'] == purchased['card_instance_id']
        and card['def_id'] == leader_offer['card_id']
        for card in bought['players']['0']['deck']
    )
    assert events[0]['type'] == 'coop_shop_purchase_completed'
    assert 'offer_id' not in events[0]

    leader_view = project_coop_run_for_viewer(_public_run(bought), 101)['snapshot']
    member_view = project_coop_run_for_viewer(_public_run(bought), 202)['snapshot']
    assert leader_view['room_state']['offers'][0].keys() == {
        'offer_id', 'card_id', 'upgraded', 'price', 'status'
    }
    assert {offer['offer_id'] for offer in leader_view['room_state']['offers']} == {
        offer['offer_id'] for offer in bought['room_states_by_player']['0']['offers']
    }
    assert {offer['offer_id'] for offer in member_view['room_state']['offers']} == {
        offer['offer_id'] for offer in member_private['offers']
    }
    assert 'card_instance_id' not in repr(leader_view['room_state']['offers'])

    with pytest.raises(CoopCombatError) as repeat_buy:
        _journey_action(
            bought,
            101,
            'shop-buy-leader-again',
            'shop_buy',
            {
                'room_id': bought['room']['id'],
                'offer_id': leader_offer['offer_id'],
            },
        )
    assert repeat_buy.value.code == 'SHOP_OFFER_ALREADY_PURCHASED'
    with pytest.raises(CoopCombatError) as forged_offer:
        _journey_action(
            bought,
            101,
            'shop-buy-other-seat',
            'shop_buy',
            {
                'room_id': bought['room']['id'],
                'offer_id': member_private['offers'][0]['offer_id'],
            },
        )
    assert forged_offer.value.code == 'INVALID_SHOP_OFFER'

    after_leave, _, _ = _journey_action(
        bought,
        101,
        'shop-leave-leader',
        'room_choose',
        {'room_id': bought['room']['id'], 'choice': 'leave'},
    )
    next_map, _, _ = _journey_action(
        after_leave,
        202,
        'shop-leave-member',
        'room_choose',
        {'room_id': bought['room']['id'], 'choice': 'leave'},
    )
    assert next_map['phase'] == 'map'


def test_shop_rejects_purchase_when_authoritative_gold_is_insufficient():
    shop = _shop_state()
    shop['players']['0']['gold'] = 0
    offer = shop['room_states_by_player']['0']['offers'][0]
    before = deepcopy(shop)
    with pytest.raises(CoopCombatError) as insufficient:
        _journey_action(
            shop,
            101,
            'shop-no-gold-buy',
            'shop_buy',
            {'room_id': shop['room']['id'], 'offer_id': offer['offer_id']},
        )
    assert insufficient.value.code == 'INSUFFICIENT_STORY_GOLD'
    assert shop == before


def test_personal_chest_relic_is_private_and_applies_compiled_acquisition_effect():
    chest = _current_room_state('chest')
    private = chest['room_states_by_player']['0']
    relic_id = private['relic_id']
    definition = COOP_STORY_CONTENT.relic_definition(relic_id)
    before_player = deepcopy(chest['players']['0'])

    leader_view = project_coop_run_for_viewer(_public_run(chest), 101)['snapshot']
    member_view = project_coop_run_for_viewer(_public_run(chest), 202)['snapshot']
    assert leader_view['room_state']['relic_id'] == relic_id
    assert member_view['room_state']['relic_id'] == chest['room_states_by_player']['1']['relic_id']
    assert leader_view['players'][0]['relics'] == before_player['relics']
    assert leader_view['players'][1]['relics'] is None

    claimed, events, _ = _journey_action(
        chest,
        101,
        'chest-leader-relic-claim',
        'room_choose',
        {'room_id': chest['room']['id'], 'choice': 'claim_relic'},
    )

    player = claimed['players']['0']
    assert relic_id in player['relics']
    if definition['script'] == 'gain_gold':
        assert player['gold'] == before_player['gold'] + definition['amount']
    elif definition['script'] == 'gain_max_health':
        assert player['max_health'] == before_player['max_health'] + definition['amount']
        assert player['health'] == before_player['health'] + definition['amount']
    assert relic_id not in repr(events)


@pytest.mark.parametrize('relic_id', ('rich', 'body_reinforcement'))
def test_compiled_chest_relic_immediate_effects_match_authoritative_catalog(relic_id):
    chest = _current_room_state('chest')
    private = chest['room_states_by_player']['0']
    private['relic_id'] = relic_id
    private['options'] = ['claim_gold', 'claim_relic', 'leave']
    before = deepcopy(chest['players']['0'])
    definition = COOP_STORY_CONTENT.relic_definition(relic_id)
    validate_coop_live_state(chest)

    claimed, _, _ = _journey_action(
        chest,
        101,
        f'chest-immediate-relic-{relic_id}',
        'room_choose',
        {'room_id': chest['room']['id'], 'choice': 'claim_relic'},
    )
    player = claimed['players']['0']
    if definition['script'] == 'gain_gold':
        assert player['gold'] == before['gold'] + definition['amount']
        assert player['max_health'] == before['max_health']
    else:
        assert definition['script'] == 'gain_max_health'
        assert player['max_health'] == before['max_health'] + definition['amount']
        assert player['health'] == before['health'] + definition['amount']


def test_greedy_adds_private_rest_gold_choice_and_server_authoritatively_pays_it():
    rest = _current_room_state('rest', seat_relics={0: ['greedy', 'greedy']})
    leader_private = rest['room_states_by_player']['0']
    member_private = rest['room_states_by_player']['1']
    amount = COOP_STORY_CONTENT.relic_definition('greedy')['amount'] * 2
    before_gold = rest['players']['0']['gold']

    assert 'gold' in leader_private['options']
    assert 'gold' not in member_private['options']
    leader_view = project_coop_run_for_viewer(_public_run(rest), 101)['snapshot']
    member_view = project_coop_run_for_viewer(_public_run(rest), 202)['snapshot']
    assert leader_view['room_state']['rest_gold'] == amount
    assert member_view['room_state']['rest_gold'] == 0

    resolved, events, _ = _journey_action(
        rest,
        101,
        'rest-greedy-gold-choice',
        'room_choose',
        {'room_id': rest['room']['id'], 'choice': 'gold'},
    )
    assert resolved['players']['0']['gold'] == before_gold + amount
    assert any(event['type'] == 'coop_rest_gold_gained' for event in events)


def test_diligent_heals_on_personal_card_reward_and_energetic_heals_on_node_completion():
    reward, _ = _finish_current_combat(_current_first_combat_state())
    reward['players']['0']['relics'].append('diligent')
    reward['players']['0']['health'] = 40
    reward['players']['1']['health'] = 40
    leader_reward = reward['rewards_by_player']['0']
    card_id = leader_reward['options'][0]['card_id']

    after_leader, events, _ = _journey_action(
        reward,
        101,
        'reward-diligent-card-gain',
        'reward_choose',
        {'reward_id': leader_reward['reward_id'], 'card_id': card_id},
    )
    assert after_leader['players']['0']['health'] == 45
    assert any(
        event['type'] == 'coop_player_healed' and event.get('source') == 'card_gain'
        for event in events
    )

    member_reward = after_leader['rewards_by_player']['1']
    on_map, events, _ = _journey_action(
        after_leader,
        202,
        'reward-node-floor-heal',
        'reward_choose',
        {'reward_id': member_reward['reward_id'], 'card_id': ''},
    )
    assert on_map['phase'] == 'map'
    assert on_map['players']['0']['health'] == 49
    assert on_map['players']['1']['health'] == 44
    assert sum(event['type'] == 'coop_player_healed' for event in events) == 2


def test_buying_bargaining_reprices_remaining_personal_shop_offers():
    from story_coop_live import _shop_relic_price

    shop = _current_room_state('shop')
    player = shop['players']['0']
    player['gold'] = 1000
    private = shop['room_states_by_player']['0']
    relic_offer = next(offer for offer in private['offers'] if offer['kind'] == 'relic')
    relic_offer.update({
        'offer_id': f"shop:{shop['current_node_id']}:seat:0:relic:0:bargaining",
        'item_id': 'bargaining',
        'relic_id': 'bargaining',
        'price': _shop_relic_price('bargaining', shop['difficulty'], player),
    })
    before_prices = {
        offer['offer_id']: offer['price']
        for offer in private['offers']
        if offer['kind'] == 'card'
    }
    validate_coop_live_state(shop)

    bought, _, _ = _journey_action(
        shop,
        101,
        'shop-buy-bargaining-reprice',
        'shop_buy',
        {'room_id': shop['room']['id'], 'offer_id': relic_offer['offer_id']},
    )

    assert 'bargaining' in bought['players']['0']['relics']
    current = bought['room_states_by_player']['0']
    for offer in current['offers']:
        if offer['kind'] == 'card' and offer['status'] == 'available':
            assert offer['price'] == max(1, before_prices[offer['offer_id']] // 2)


def test_buying_second_bargaining_stacks_and_keeps_shop_state_valid():
    from story_coop_live import _shop_relic_price

    shop = _current_room_state('shop', seat_relics={0: ['bargaining']})
    player = shop['players']['0']
    player['gold'] = 1000
    private = shop['room_states_by_player']['0']
    relic_offer = next(offer for offer in private['offers'] if offer['kind'] == 'relic')
    relic_offer.update({
        'offer_id': f"shop:{shop['current_node_id']}:seat:0:relic:0:bargaining",
        'item_id': 'bargaining',
        'relic_id': 'bargaining',
        'price': _shop_relic_price('bargaining', shop['difficulty'], player),
    })
    before_prices = {
        offer['offer_id']: offer['price']
        for offer in private['offers']
        if offer['kind'] == 'card'
    }
    validate_coop_live_state(shop)

    bought, _, _ = _journey_action(
        shop,
        101,
        'shop-buy-second-bargaining',
        'shop_buy',
        {'room_id': shop['room']['id'], 'offer_id': relic_offer['offer_id']},
    )

    assert bought['players']['0']['relics'].count('bargaining') == 2
    current = bought['room_states_by_player']['0']
    for offer in current['offers']:
        if offer['kind'] == 'card' and offer['status'] == 'available':
            assert offer['price'] == max(1, before_prices[offer['offer_id']] // 2)
    validate_coop_live_state(bought)


def test_current_relic_and_shop_corruption_fail_closed_without_mutating_source():
    shop = _current_room_state('shop')
    bad_relic = deepcopy(shop)
    bad_relic['players']['0']['relics'].append('unsupported-private-relic')
    with pytest.raises(CoopCombatError) as relic_error:
        validate_coop_live_state(bad_relic)
    assert relic_error.value.code == 'UNSUPPORTED_COOP_RELIC'

    bad_price = deepcopy(shop)
    bad_price['room_states_by_player']['0']['offers'][0]['price'] += 1
    with pytest.raises(CoopCombatError) as price_error:
        validate_coop_live_state(bad_price)
    assert price_error.value.code == 'INVALID_COOP_ROOM'
    assert shop == _current_room_state('shop')


def test_shared_event_hides_votes_and_resolves_unanimously_without_rng():
    event = _event_state()
    event['players']['0']['health'] = 50
    event['players']['1']['health'] = 60
    room_id = event['room']['id']
    stream = f'coop_event_vote:{room_id}'
    before = deepcopy(event)
    after_first, first_events, _ = _journey_action(
        event,
        101,
        'event-mend-leader',
        'room_choose',
        {'room_id': room_id, 'choice': 'mend'},
    )
    assert event == before
    assert stream not in after_first['rng_streams']
    assert after_first['phase'] == 'room'
    assert first_events[0]['type'] == 'coop_event_vote_cast'
    assert 'choice' not in first_events[0]
    member_view = project_coop_run_for_viewer(_public_run(after_first), 202)['snapshot']
    assert member_view['room_state']['seats'] == [
        {'seat': 0, 'submitted': True},
        {'seat': 1, 'submitted': False},
    ]
    assert [
        option['id'] for option in member_view['room_state']['option_definitions']
    ] == ['mend', 'supplies', 'risk']
    assert member_view['room_state']['option_definitions'][0]['label']['zh'] == '修整工具'
    assert all(
        'effects' not in option
        for option in member_view['room_state']['option_definitions']
    )
    assert 'votes_by_seat' not in repr(member_view)
    resolved, events, _ = _journey_action(
        after_first,
        202,
        'event-mend-member',
        'room_choose',
        {'room_id': room_id, 'choice': 'mend'},
    )
    assert stream not in resolved['rng_streams']
    assert resolved['phase'] == 'map'
    assert resolved['players']['0']['health'] == 65
    assert resolved['players']['1']['health'] == 75
    outcome = next(item for item in events if item['type'] == 'coop_event_resolved')
    assert outcome['choice'] == 'mend'
    assert outcome['content_id'] == 'coop_garden_crossroads'
    assert outcome['reason'] == 'unanimous'


def test_split_event_vote_applies_nothing_and_requires_unanimous_retry():
    event = _event_state()
    event['players']['0']['health'] = 50
    event['players']['1']['health'] = 50
    before_gold = {seat: player['gold'] for seat, player in event['players'].items()}
    room_id = event['room']['id']
    stream = f'coop_event_vote:{room_id}'
    after_first, _, _ = _journey_action(
        event,
        101,
        'event-split-leader',
        'room_choose',
        {'room_id': room_id, 'choice': 'supplies'},
    )
    retry, events, _ = _journey_action(
        after_first,
        202,
        'event-split-member',
        'room_choose',
        {'room_id': room_id, 'choice': 'risk'},
    )
    assert stream not in retry['rng_streams']
    assert retry['phase'] == 'room'
    assert retry['coordination']['room_decision']['votes_by_seat'] == {}
    assert retry['coordination']['room_decision']['resolved_seats'] == []
    assert all(
        private['status'] == 'pending' and private['selected_option'] is None
        for private in retry['room_states_by_player'].values()
    )
    assert all(player['health'] == 50 for player in retry['players'].values())
    assert {seat: player['gold'] for seat, player in retry['players'].items()} == before_gold
    assert [event['type'] for event in events] == [
        'coop_event_vote_cast',
        'coop_event_consensus_required',
    ]

    agreed_first, _, _ = _journey_action(
        retry,
        101,
        'event-retry-leader',
        'room_choose',
        {'room_id': room_id, 'choice': 'supplies'},
    )
    resolved, resolved_events, _ = _journey_action(
        agreed_first,
        202,
        'event-retry-member',
        'room_choose',
        {'room_id': room_id, 'choice': 'supplies'},
    )
    assert stream not in resolved['rng_streams']
    assert resolved['phase'] == 'map'
    outcome = next(item for item in resolved_events if item['type'] == 'coop_event_resolved')
    assert outcome['choice'] == 'supplies'
    assert outcome['reason'] == 'unanimous'
    assert all(
        resolved['players'][seat]['gold'] == before_gold[seat] + 30
        for seat in resolved['players']
    )


def test_compiled_story_event_edit_changes_new_coop_run_resolution(monkeypatch):
    authored_events = deepcopy(STORY_EVENTS)
    authored_events['coop_garden_crossroads']['options'][0]['effects'][0]['amount'] = 21
    compiled = compile_coop_story_content(events=authored_events)
    content_version = (
        f'{story_coop_live.STORY_CONTENT_VERSION}-coop-stage1-shared-content-1-'
        f'{compiled.fingerprint[:12]}'
    )
    monkeypatch.setattr(story_coop_live, 'COOP_STORY_CONTENT', compiled)
    monkeypatch.setattr(story_coop_live, 'COOP_STORY_CONTENT_VERSION', content_version)

    event = _current_room_state('event')
    event['players']['0']['health'] = 40
    event['players']['1']['health'] = 40
    event['players']['0']['relics'] = []
    event['players']['1']['relics'] = []
    room_id = event['room']['id']
    first, _, _ = _journey_action(
        event,
        101,
        'compiled-event-edit-leader',
        'room_choose',
        {'room_id': room_id, 'choice': 'mend'},
    )
    resolved, _, _ = _journey_action(
        first,
        202,
        'compiled-event-edit-member',
        'room_choose',
        {'room_id': room_id, 'choice': 'mend'},
    )

    assert resolved['players']['0']['health'] == 61
    assert resolved['players']['1']['health'] == 61


def test_previous_shared_event_snapshot_keeps_frozen_definition():
    event = _current_room_state('event')
    event['content_version'] = (
        f'{story_coop_live.STORY_CONTENT_VERSION}-coop-stage1-shared-content-1-'
        '000000000000'
    )
    assert validate_coop_live_state(event) is True
    frozen_snapshot = project_coop_run_for_viewer(_public_run(event), 101)['snapshot']
    assert 'content_snapshot' not in repr(frozen_snapshot)
    assert 'effects' not in repr(frozen_snapshot['room_state']['option_definitions'])

    legacy = story_coop_live.COOP_LEGACY_GARDEN_EVENT_DEFINITION
    event['room'].pop('content_snapshot', None)
    event['room']['title'] = deepcopy(legacy['title'])
    event['room']['description'] = deepcopy(legacy['description'])
    event['room']['policy'] = legacy['coop']['policy']
    event['coordination']['room_decision']['policy'] = legacy['coop']['policy']

    assert validate_coop_live_state(event) is True
    snapshot = project_coop_run_for_viewer(_public_run(event), 101)['snapshot']
    assert snapshot['room']['title'] == legacy['title']
    assert [
        option['id'] for option in snapshot['room_state']['option_definitions']
    ] == ['mend', 'supplies', 'risk']


def test_current_shared_event_snapshot_corruption_fails_closed():
    event = _current_room_state('event')
    event['room']['content_snapshot']['options'][0]['effects'][0]['amount'] += 1

    with pytest.raises(CoopCombatError) as exc_info:
        validate_coop_live_state(event)

    assert exc_info.value.code == 'INVALID_COOP_ROOM'


def test_legacy_two_encounter_state_uses_frozen_validator_and_projection():
    legacy = deepcopy(_intro_state())
    legacy['content_version'] = COOP_LEGACY_CONTENT_VERSION
    legacy['coop_progression'] = {
        'chapter': 1,
        'encounter_index': 1,
        'max_encounters': 2,
        'completed_combat_ids': [],
    }
    legacy.pop('room_states_by_player', None)

    assert validate_coop_live_state(legacy) is True
    snapshot = project_coop_run_for_viewer(_public_run(legacy), 101)['snapshot']
    assert snapshot['progression']['max_encounters'] == 2
    assert 'contract_version' not in snapshot['progression']


def _complete_controlled_stage():
    state = _intro_state()
    action_index = 0
    final_events = []
    for _ in range(80):
        phase = state['phase']
        if phase == 'combat':
            state, final_events = _finish_current_combat(state)
        elif phase == 'reward':
            for seat, user_id in ((0, 101), (1, 202)):
                reward = state['rewards_by_player'][str(seat)]
                action_index += 1
                state, final_events, _ = _journey_action(
                    state,
                    user_id,
                    f'full-stage-reward-{action_index}',
                    'reward_choose',
                    {'reward_id': reward['reward_id'], 'card_id': ''},
                )
        elif phase == 'map':
            vote = state['coordination']['map_vote']
            selected = vote['option_node_ids'][0]
            for user_id in (101, 202):
                action_index += 1
                state, final_events, _ = _journey_action(
                    state,
                    user_id,
                    f'full-stage-route-{action_index}',
                    'map_vote',
                    {'vote_id': vote['vote_id'], 'node_id': selected},
                )
        elif phase == 'room':
            room_id = state['room']['id']
            for user_id in (101, 202):
                action_index += 1
                seat = 0 if user_id == 101 else 1
                options = state['room_states_by_player'][str(seat)]['options']
                choice = 'leave' if 'leave' in options else options[0]
                state, final_events, _ = _journey_action(
                    state,
                    user_id,
                    f'full-stage-room-{action_index}',
                    'room_choose',
                    {'room_id': room_id, 'choice': choice},
                )
        elif phase == 'stage_complete':
            break
        else:
            raise AssertionError(f'unexpected controlled stage phase: {phase}')
        validate_coop_live_state(state)
    else:
        raise AssertionError('controlled cooperative stage did not terminate')
    return state, final_events, action_index


def _complete_current_stage(state, *, prefix='current-stage'):
    action_index = 0
    final_events = []
    for _ in range(160):
        phase = state['phase']
        if phase == 'combat':
            state, final_events = _finish_current_combat(state)
        elif phase == 'reward':
            for seat, user_id in ((0, 101), (1, 202)):
                reward = state['rewards_by_player'][str(seat)]
                action_index += 1
                state, final_events, _ = _journey_action(
                    state,
                    user_id,
                    f'{prefix}-reward-{action_index:04d}',
                    'reward_choose',
                    {'reward_id': reward['reward_id'], 'card_id': ''},
                )
        elif phase == 'map':
            vote = state['coordination']['map_vote']
            node_id = vote['option_node_ids'][0]
            for user_id in (101, 202):
                action_index += 1
                state, final_events, _ = _journey_action(
                    state,
                    user_id,
                    f'{prefix}-route-{action_index:04d}',
                    'map_vote',
                    {'vote_id': vote['vote_id'], 'node_id': node_id},
                )
        elif phase == 'room':
            room_type = state['room']['type']
            room_id = state['room']['id']
            for seat, user_id in ((0, 101), (1, 202)):
                private = state['room_states_by_player'][str(seat)]
                action_index += 1
                if room_type == 'opening':
                    action_type = 'opening_choose'
                    payload = {'room_id': room_id, 'option_id': private['options'][0]}
                else:
                    action_type = 'room_choose'
                    choice = 'leave' if 'leave' in private['options'] else private['options'][0]
                    payload = {'room_id': room_id, 'choice': choice}
                state, final_events, _ = _journey_action(
                    state,
                    user_id,
                    f'{prefix}-room-{action_index:04d}',
                    action_type,
                    payload,
                )
        elif phase == 'stage_complete':
            return state, final_events, action_index
        else:
            raise AssertionError(f'unexpected controlled stage phase: {phase}')
        validate_coop_live_state(state)
    raise AssertionError('controlled current cooperative stage did not terminate')


def test_controlled_stage_one_path_reaches_explicit_stage_complete_without_dead_ends():
    state, final_events, action_index = _complete_controlled_stage()

    assert state['phase'] == 'stage_complete'
    assert state['completed'] is False
    assert state['completed_stage'] == 1
    assert state['current_floor'] == state['coop_progression']['max_floor']
    assert len(state['coop_progression']['completed_node_ids']) == state['current_floor']
    assert state['room']['type'] == 'stage_complete'
    assert any(event['type'] == 'coop_stage_completed' for event in final_events)
    public = project_coop_run_for_viewer(
        _public_run(state, status='completed', revision=action_index + 1),
        101,
    )['snapshot']
    assert public['phase'] == 'stage_complete'
    assert public['progression']['completed_stage'] == 1


def test_both_members_must_confirm_before_stage_two_map_and_blessing_begin():
    state, _, action_index = _complete_current_stage(_current_initial_map_state())
    assert state['phase'] == 'stage_complete'
    assert state['coop_progression']['completed_stages'] == [1]
    for player in state['players'].values():
        player['health'] = 10
    room_id = state['room']['id']

    leader_ready, _, _ = _journey_action(
        state,
        101,
        f'current-stage-ready-{action_index + 1:04d}',
        'stage_ready',
        {'room_id': room_id},
    )
    assert leader_ready['phase'] == 'stage_complete'
    assert leader_ready['room_states_by_player']['0']['status'] == 'resolved'
    assert leader_ready['room_states_by_player']['1']['status'] == 'pending'

    stage_two, events, _ = _journey_action(
        leader_ready,
        202,
        f'current-stage-ready-{action_index + 2:04d}',
        'stage_ready',
        {'room_id': room_id},
    )
    assert stage_two['phase'] == 'room'
    assert stage_two['room']['type'] == 'opening'
    assert stage_two['stage'] == 2
    assert stage_two['biome'] == 'jungle'
    assert stage_two['map']['stage'] == 2
    assert stage_two['map']['biome'] == 'jungle'
    assert stage_two['coop_progression']['completed_stages'] == [1]
    assert stage_two['completed_stage'] == 1
    assert all(
        player['health'] == player['max_health']
        for player in stage_two['players'].values()
    )
    assert any(event['type'] == 'coop_stage_started' for event in events)
    assert validate_coop_live_state(stage_two) is True


def test_stage_complete_rejects_a_skipped_completed_route_even_when_ids_match():
    state, _, _ = _complete_controlled_stage()
    completed = state['coop_progression']['completed_node_ids']
    first_node_id = completed[0]
    boss_node_id = completed[-1]
    for floor in state['map']['floors']:
        for node in floor['nodes']:
            if node['status'] == 'completed' and node['id'] not in {
                first_node_id,
                boss_node_id,
            }:
                node['status'] = 'locked'
    state['coop_progression']['completed_node_ids'] = [first_node_id, boss_node_id]
    state['coop_progression']['completed_combat_ids'] = [
        COOP_INTRO_COMBAT_ID,
        state['last_combat']['id'],
    ]
    state['coop_progression']['encounter_index'] = 2

    with pytest.raises(CoopCombatError) as exc_info:
        validate_coop_live_state(state)
    assert exc_info.value.code == 'INVALID_COOP_PROGRESSION'


@pytest.mark.parametrize(
    'corruption',
    (
        'missing_edges',
        'terminal_not_boss',
        'forged_floor_count',
        'boolean_stage',
        'negative_rng',
    ),
)
def test_current_stage_validator_rejects_corrupt_map_and_rng_before_progression(
    corruption,
):
    state = _intro_state()
    if corruption == 'missing_edges':
        state['map']['edges'] = []
    elif corruption == 'terminal_not_boss':
        state['map']['floors'][-1]['nodes'][0]['type'] = 'rest'
    elif corruption == 'forged_floor_count':
        state['map']['floor_count'] = 99
        state['coop_progression']['max_floor'] = 99
    elif corruption == 'boolean_stage':
        state['stage'] = True
        state['map']['stage'] = True
    else:
        state['rng_streams']['unused-but-corrupt'] = -1

    with pytest.raises(CoopCombatError) as exc_info:
        validate_coop_live_state(state)
    assert exc_info.value.code in {'INVALID_COOP_MAP', 'INVALID_RNG_STATE'}


def test_reward_and_vote_projection_hide_other_seat_choices_and_server_state():
    reward = _reward_state()
    leader = project_coop_run_for_viewer(_public_run(reward), 101)['snapshot']
    member = project_coop_run_for_viewer(_public_run(reward), 202)['snapshot']

    assert leader['reward']['options'] == reward['rewards_by_player']['0']['options']
    assert member['reward']['options'] == reward['rewards_by_player']['1']['options']
    assert all(set(item) == {'seat', 'resolved'} for item in leader['reward']['seats'])
    assert 'rewards_by_player' not in repr(leader)

    map_state, _ = _map_state()
    vote = map_state['coordination']['map_vote']
    selected = vote['option_node_ids'][0]
    after_vote, _, _ = _journey_action(
        map_state,
        101,
        'progress-private-vote',
        'map_vote',
        {'vote_id': vote['vote_id'], 'node_id': selected},
    )
    leader_map = project_coop_run_for_viewer(_public_run(after_vote, revision=2), 101)
    member_map = project_coop_run_for_viewer(_public_run(after_vote, revision=2), 202)

    assert leader_map['snapshot']['map_vote']['viewer_node_id'] == selected
    assert member_map['snapshot']['map_vote']['viewer_node_id'] is None
    assert all(set(item) == {'seat', 'submitted'} for item in member_map['snapshot']['map_vote']['seats'])
    public_keys = _nested_keys(member_map)
    for private_name in ('seed', 'rng_streams', 'draw_pile', 'action_receipts', 'request_fingerprint'):
        assert private_name not in public_keys


def test_live_validator_rejects_cross_phase_and_identity_corruption():
    intro = _intro_state()
    reward = _reward_state()

    invalid_states = []

    wrong_index = deepcopy(intro)
    wrong_index['coop_progression']['encounter_index'] = 2
    invalid_states.append(wrong_index)

    wrong_encounter = deepcopy(intro)
    wrong_encounter['combat']['encounter_id'] = COOP_SECOND_ENCOUNTER_ID
    invalid_states.append(wrong_encounter)

    wrong_completed_shape = deepcopy(intro)
    wrong_completed_shape['coop_progression']['completed_combat_ids'] = COOP_INTRO_COMBAT_ID
    invalid_states.append(wrong_completed_shape)

    unhashable_completed_id = deepcopy(intro)
    unhashable_completed_id['coop_progression']['completed_combat_ids'] = [{}]
    invalid_states.append(unhashable_completed_id)

    fake_complete = deepcopy(intro)
    fake_complete['phase'] = 'complete'
    fake_complete['completed'] = True
    fake_complete['combat'] = None
    fake_complete['coordination']['combat_ready_seats'] = []
    fake_complete['coordination']['combat_ready_round'] = None
    fake_complete['room'] = {'type': 'coop_complete'}
    invalid_states.append(fake_complete)

    wrong_reward_id = deepcopy(reward)
    wrong_reward_id['rewards_by_player']['1']['reward_id'] = 'reward:wrong:seat:1'
    invalid_states.append(wrong_reward_id)

    empty_reward = deepcopy(reward)
    empty_reward['rewards_by_player']['0']['options'] = []
    invalid_states.append(empty_reward)

    malformed_vote, _ = _map_state()
    malformed_vote['coordination']['map_vote']['option_node_ids'] = [{}]
    invalid_states.append(malformed_vote)

    for state in invalid_states:
        with pytest.raises(CoopCombatError):
            validate_coop_live_state(state)
