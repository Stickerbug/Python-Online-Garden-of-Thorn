# -*- coding: utf-8 -*-
"""本地 E2E：合作模式可玩牌读视角投影（2026-10-12 修复验证）。

复现线上 bug：playable_card_ids/damage_predictions 是共享键、按当前挂载席
手牌计算——席A动作后刷新的是A的列表，席B GET 时手牌已换成B的但列表还是
A的，B 的部分手牌被前端误禁用。修复后读路径为观看席重算投影。

跑法：.venv/Scripts/python.exe tests/local_e2e_coop_playable.py
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
from app import _COOP_DEMO_RUNS  # noqa: E402
import story_mode  # noqa: E402
from story_engine import (  # noqa: E402
    _is_card_playable,
    _mount_seat,
    _refresh_combat_projections,
    _start_combat,
)

STAFF_USER_ID = 1  # Q12

client = app_module.app.test_client()
with client.session_transaction() as sess:
    sess['user_id'] = STAFF_USER_ID

# --- 开局并注入一场双席战斗 ---
r = client.post('/api/coop-demo/start', json={})
assert r.status_code == 200, r.get_data(as_text=True)
entry = _COOP_DEMO_RUNS[STAFF_USER_ID]
state = story_mode.build_initial_story_state('e2e-play', 'common_flower')
state['players'] = [copy.deepcopy(state['player']), copy.deepcopy(state['player'])]
state['coord'] = {}
ev = []
_start_combat(state, {'type': 'combat'}, 'e2e-play', ev,
              encounter_override=[{'def_id': 'mechanical_crab'}])
entry['state'] = state
entry['version'] = 1

def expected_playable(shared_state, seat):
    """独立副本上按引擎口径计算 seat 的可玩列表（作为对照真值）。"""
    probe = copy.deepcopy(shared_state)
    _mount_seat(probe, seat)
    _refresh_combat_projections(probe)
    return set(probe['combat']['playable_card_ids'])

def get_run(seat):
    resp = client.get(f'/api/coop-demo/run?seat={seat}')
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()['run']

# 1) 席0视角：可玩列表 == 席0手牌口径
run0 = get_run(0)
got0 = set(run0['state']['combat']['playable_card_ids'])
exp0 = expected_playable(state, 0)
assert got0 == exp0, f'席0列表不符: got={sorted(got0)} exp={sorted(exp0)}'
print(f'[1] 席0 可玩 {len(got0)}/{len(run0["state"]["combat"]["hand"])} 与引擎口径一致 OK')

# 2) 席1视角：可玩列表必须按席1手牌重算（修复前这里是席0的列表）
run1 = get_run(1)
got1 = set(run1['state']['combat']['playable_card_ids'])
exp1 = expected_playable(state, 1)
assert got1 == exp1, f'席1列表不符: got={sorted(got1)} exp={sorted(exp1)}'
print(f'[2] 席1 可玩 {len(got1)}/{len(run1["state"]["combat"]["hand"])} 与引擎口径一致 OK')

# 3) 两席手牌不同 → 列表应不同（回归守卫：共享残留会让两席列表相同/错位）
if run0['state']['combat']['hand'] != run1['state']['combat']['hand']:
    assert got0 != got1 or (not got0 and not got1), '两席手牌不同但可玩列表相同：疑似共享残留'
    print('[3] 两席手牌不同 → 可玩列表各自独立 OK')

# 4) 席0打一张牌后，席1读视角仍为本席口径（动作写路径刷新的是行动席）
resp = client.post('/api/coop-demo/action', json={
    'action_type': 'dev_give_card', 'demo_seat': 0, 'payload': {'card_id': 'basic'},
})
assert resp.get_json().get('success'), resp.get_json()
state = entry['state']
basic_card = next(c for c in state['combat']['hand'] if c.get('def_id') == 'basic')
resp = client.post('/api/coop-demo/action', json={
    'action_type': 'play_card', 'demo_seat': 0,
    'payload': {'card_instance_id': basic_card['instance_id'],
                'target_id': state['combat']['enemies'][0]['id']},
})
body = resp.get_json()
assert resp.status_code == 200 and body.get('success'), body
state = entry['state']
run1_after = get_run(1)
got1a = set(run1_after['state']['combat']['playable_card_ids'])
exp1a = expected_playable(state, 1)
assert got1a == exp1a, f'动作后席1列表不符: got={sorted(got1a)} exp={sorted(exp1a)}'
print('[4] 席0出牌后席1读视角仍为本席口径 OK')

print('\n全部通过：可玩牌读视角投影 E2E 验证成功')
