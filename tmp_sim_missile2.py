# -*- coding: utf-8 -*-
"""Simulate: missile on draw top, play a draw-effect card -> ready auto-play chain."""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from story_engine import _start_combat, _new_card, _card_values, apply_story_action
from story_mode import build_initial_story_state

state = build_initial_story_state('sim-chain', character_id='mage')
_start_combat(state, {'type': 'combat'}, 'sim-chain', [],
              encounter_override=[{'def_id': 'soldier_ant'}])
combat = state['combat']

# Missile on top of draw pile (end of list)
missile = _new_card(state, 'mage_electronic_missile')
combat['draw_pile'].append(missile)

# A draw card in hand: use mage_missile (damage 15, draw 3)
draw_card = _new_card(state, 'mage_missile')
combat['hand'].append(draw_card)
combat['magic'] = 10
print('magic before: %s' % (state['player'].get('magic') if 'magic' in state['player'] else combat.get('magic')))
print('combat keys: magic=%s' % combat.get('magic'))
target_id = combat['enemies'][0]['id']
state, events = apply_story_action(
    state, 'play_card',
    {'card_instance_id': draw_card['instance_id'], 'target_id': target_id},
    'sim-chain',
)
combat = state['combat']
print('AFTER: hand=%s' % [c['def_id'] for c in combat['hand']])
print('draw=%s' % [c['def_id'] for c in combat['draw_pile']])
print('discard=%s' % [c['def_id'] for c in combat['discard_pile']])
print('exile=%s' % [c['def_id'] for c in combat.get('exile_pile', [])])
for e in events:
    if e.get('type') in ('card_played', 'card_discarded', 'draw', 'card_created',
                         'hand_overflow', 'reshuffle', 'magic_spent'):
        print('  %s: %s' % (e.get('type'), {
            'def_id': e.get('def_id'), 'count': e.get('count'),
            'reason': e.get('reason'), 'amount': e.get('amount')}))
