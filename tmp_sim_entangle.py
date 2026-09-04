# -*- coding: utf-8 -*-
"""Verify entangle persists after fix."""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from story_engine import _start_combat, _end_turn
from story_mode import build_initial_story_state

state = build_initial_story_state('sim-entangle')
_start_combat(
    state,
    {'type': 'combat'},
    'sim-entangle',
    [],
    encounter_override=[{'def_id': 'squid'}],
)
combat = state['combat']
combat['entangle'] = 5
combat['blockade'] = 2
print('BEFORE: entangle=%s blockade=%s health=%s' % (
    combat.get('entangle'), combat.get('blockade'), state['player']['health']))
for i in range(3):
    events = []
    _end_turn(state, 'sim-entangle', events)
    print('CYCLE %s: entangle=%s blockade=%s health=%s' % (
        i + 1, combat.get('entangle'), combat.get('blockade'), state['player']['health']))
    for e in events:
        if e.get('type') == 'player_damage' and e.get('source') == 'entangle':
            print('  entangle damage: %s' % e.get('amount'))
