# -*- coding: utf-8 -*-
"""Debug why second missile play doesn't trigger static."""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from story_engine import _start_combat, apply_story_action
from story_mode import build_initial_story_state

state = build_initial_story_state('dbg')
state['player']['health'] = 9999
state['player']['max_health'] = 9999
events = []
_start_combat(state, {'type': 'combat'}, 'dbg', events,
              encounter_override=[{'def_id': 'soldier_ant'}])
combat = state['combat']
combat['opening_redraw_pending'] = False
combat['elixir'] = 100
combat['magic'] = 100
combat['draw_pile'] = [
    {'instance_id': 'dbg-draw-basic', 'def_id': 'basic', 'upgraded': False},
    {'instance_id': 'dbg-draw-magic', 'def_id': 'mage_basic', 'upgraded': False},
]
combat['discard_pile'] = [{'instance_id': 'dbg-discard', 'def_id': 'rose', 'upgraded': False}]
enemy = combat['enemies'][0]
enemy['health'] = enemy['max_health'] = 1_000_000

def play(card_id, suffix):
    global state
    combat = state['combat']
    card = {'instance_id': f'{card_id}-{suffix}', 'def_id': card_id, 'upgraded': False}
    filler = {'instance_id': f'{card_id}-{suffix}-filler', 'def_id': 'basic', 'upgraded': False}
    combat['hand'] = [card, filler]
    state, evts = apply_story_action(
        state, 'play_card',
        {'card_instance_id': card['instance_id'], 'target_enemy_id': combat['enemies'][0]['id']},
        f'dbg-{suffix}',
    )
    return evts

ev1 = play('electronic_missile', 'first')
print('after first: static=%s hp=%s' % (
    state['combat']['enemies'][0]['static'], state['combat']['enemies'][0]['health']))
print('hand: %s' % [c['def_id'] for c in state['combat']['hand']])
ev2 = play('mage_electronic_missile', 'second')
print('after second: static=%s hp=%s' % (
    state['combat']['enemies'][0]['static'], state['combat']['enemies'][0]['health']))
for e in ev2:
    print('  %s: %s' % (e.get('type'), {k: v for k, v in e.items() if k in (
        'def_id', 'amount', 'static_applied', 'static_consumed', 'count')}))
