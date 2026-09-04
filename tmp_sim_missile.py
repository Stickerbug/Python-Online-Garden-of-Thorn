# -*- coding: utf-8 -*-
"""Full-cycle simulation: play missile, end turn, next turn draws, ready auto-play."""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from story_engine import (
    _start_combat, _end_turn, _new_card, _card_values, apply_story_action,
)
from story_mode import build_initial_story_state


def piles(combat):
    return {
        'hand': [c['def_id'] for c in combat['hand']],
        'draw': [c['def_id'] for c in combat['draw_pile']],
        'discard': [c['def_id'] for c in combat['discard_pile']],
        'exile': [c['def_id'] for c in combat.get('exile_pile', [])],
    }


def run(def_id, upgraded=False):
    print('=' * 70)
    print('SIM: %s upgraded=%s' % (def_id, upgraded))
    state = build_initial_story_state('sim-' + def_id, character_id='mage')
    _start_combat(
        state,
        {'type': 'combat'},
        'sim',
        [],
        encounter_override=[{'def_id': 'soldier_ant'}],
    )
    combat = state['combat']
    card = _new_card(state, def_id, upgraded=upgraded)
    combat['hand'].append(card)
    combat['magic'] = 5
    print('values: cost_e=%s cost_m=%s effects=%s script=%s tags=%s' % (
        _card_values(card).get('cost_e'), _card_values(card).get('cost_m'),
        [e.get('type') for e in _card_values(card).get('effects') or ()],
        _card_values(card).get('script'), _card_values(card).get('tags')))
    target_id = combat['enemies'][0]['id']
    state, events = apply_story_action(
        state,
        'play_card',
        {'card_instance_id': card['instance_id'], 'target_id': target_id},
        'sim',
    )
    combat = state['combat']
    print('AFTER PLAY: %s' % piles(combat))
    print('enemy hp: %s static: %s' % (
        combat['enemies'][0]['health'], combat['enemies'][0].get('static')))
    for turn in range(2):
        events = []
        _end_turn(state, 'sim', events)
        combat = state['combat']
        interesting = [
            e for e in events
            if e.get('type') in ('card_discarded', 'card_played', 'draw',
                                 'card_created', 'hand_overflow', 'reshuffle')
        ]
        print('  TURN %s key events:' % (turn + 1))
        for e in interesting:
            print('    %s: card=%s count=%s reason=%s' % (
                e.get('type'),
                e.get('def_id') or e.get('card_instance_id'),
                e.get('count'), e.get('reason')))
        print('  piles: %s' % piles(combat))
        if state.get('phase') != 'combat':
            print('  combat ended')
            break


run('mage_electronic_missile')
run('mage_electronic_missile', upgraded=True)
run('mage_orange')
run('mage_orange', upgraded=True)
