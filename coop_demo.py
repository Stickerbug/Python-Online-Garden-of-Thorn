# -*- coding: utf-8 -*-
"""双席合作战斗演示：用真实主引擎跑一场 2v1 对局（尚无前端，纯引擎驱动）。"""
import copy

import story_mode
from story_engine import (
    _mount_seat,
    _start_combat,
    apply_story_action,
    _card_values,
)

SEED = 'demo-coop-1'
state = story_mode.build_initial_story_state(SEED, 'common_flower')
state['players'] = [copy.deepcopy(state['player']), copy.deepcopy(state['player'])]
state['players'][1]['character_id'] = 'orbiter'  # 仅作展示标注（按席位角色在后续步骤实装）

events0 = []
_start_combat(state, {'type': 'combat'}, SEED, events0,
              encounter_override=[{'def_id': 'mechanical_crab'}])

combat = state['combat']


def seat_brief(seat):
    _mount_seat(state, seat)
    cards = ', '.join(
        f"{_card_values(c).get('name', {}).get('zh', c['def_id'])}({int(c.get('cost_e') or 0)}E)"
        for c in combat['hand'][:5]
    )
    p = state['players'][seat]
    return (f"席{seat} H{int(p['health'])}/{int(p['max_health'])} "
            f"E{combat['elixir']} 盾{combat['shield']} | 手牌: {cards}")


def play(seat, hand_index, note=''):
    global state, combat
    _mount_seat(state, seat)
    card = combat['hand'][hand_index]
    name = _card_values(card).get('name', {}).get('zh', card['def_id'])
    payload = {'card_instance_id': card['instance_id']}
    if card.get('target_kind') == 'enemy' or True:
        payload['target_id'] = combat['enemies'][0]['id']
    state, ev = apply_story_action(state, 'play_card', payload, SEED)
    combat = state['combat']
    dmg = sum(int(e.get('amount') or 0) for e in ev if e.get('type') == 'enemy_damage')
    print(f"  席{seat} 打出 {name}{note} → 对敌造成 {dmg} 伤害"
          f"（螃蟹剩 {int(combat['enemies'][0]['health'])}H）")
    return state


def ready(seat):
    global state, combat
    _mount_seat(state, seat)
    state, ev = apply_story_action(state, 'end_turn', {}, SEED)
    combat = state['combat']
    for e in ev:
        if e.get('type') == 'combat_seat_ready':
            print(f"  席{seat} 点了【结束回合】（就绪）"
                  f"{'——全员就绪，进入敌方回合！' if e.get('all_ready') else '，等待席{0 if seat else 1}…'}")
    for e in ev:
        if e.get('type') == 'enemy_action':
            move = e.get('source_definition_id')
        if e.get('type') == 'player_damage':
            print(f"    ⚔ 螃蟹攻击 → 席{e.get('seat', '?')} 受到 {e.get('amount')} 伤害"
                  f"（该席剩 {e.get('after')}H）")
        if e.get('type') == 'enemy_skipped':
            print('    💤 螃蟹被眩晕跳过')
        if e.get('type') == 'seat_downed':
            print(f"    💀 席{e.get('seat')} 倒地！（战斗继续，另一席可救场）")
        if e.get('type') == 'seat_revived':
            print(f"    ✨ 胜利结算：席{e.get('seat')} 复活至 {e.get('after')}H")
    return state


print('=== 双人合作 · 花园战斗 vs 机械螃蟹（引擎实录） ===\n')
print('【第1回合 · 英雄阶段（两席同时行动）】')
print(' ', seat_brief(0))
print(' ', seat_brief(1))
play(0, 0)
play(1, 0)
play(0, 1)
ready(0)
ready(1)

print(f'\n【第2回合】螃蟹: {int(combat["enemies"][0]["health"])}H，意图:'
      f' {combat["enemies"][0].get("intent", {}).get("name", "连击")}')
print(' ', seat_brief(0))
print(' ', seat_brief(1))
play(0, 0)
ready(0)
ready(1)

print('\n【终局】')
print(' ', seat_brief(0))
print(' ', seat_brief(1))
print(f'  阶段: {state["phase"]}（reward=胜利结算，combat=None 表示战斗已结束）')
