# -*- coding: utf-8 -*-
"""本地 E2E：合作奖励读视角投影（2026-10-12 修复验证）。

复现线上 bug：一席选完奖励后，另一席 GET /api/coop-demo/run 看到的
state.reward 为空 → 前端只剩"跳过"。修复后 GET/动作响应都投影本席待选奖励。

跑法：.venv/Scripts/python.exe tests/local_e2e_coop_reward.py
（不走浏览器；引擎语义由 test_coop_orchestration.py 覆盖，这里只验 HTTP 层。）
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
from app import (  # noqa: E402
    _COOP_DEMO_RUNS,
    _coop_demo_allowed,
)

STAFF_USER_ID = 1  # Q12：本地库（线上库副本）里的 admin

client = app_module.app.test_client()
with client.session_transaction() as sess:
    sess['user_id'] = STAFF_USER_ID

assert _coop_demo_allowed(STAFF_USER_ID), '本地库中 Q12 需有 admin/staff 角色'

# --- 开一局个人演示（不建房间：GET ?seat= / 动作 demo_seat= 可模拟两席） ---
r = client.post('/api/coop-demo/start', json={})
assert r.status_code == 200, r.get_data(as_text=True)
entry = _COOP_DEMO_RUNS[STAFF_USER_ID]
state = entry['state']

# --- 注入战斗胜利后的奖励阶段（引擎路径由单测覆盖） ---
state['phase'] = 'reward'
state['reward'] = {'gold': 30, 'cards': ['basic', 'rose'], 'claims': {}, 'source': 'combat'}

def get_run(seat):
    resp = client.get(f'/api/coop-demo/run?seat={seat}')
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()['run']

def act(seat, payload):
    resp = client.post('/api/coop-demo/action', json={
        'action_type': payload.pop('_type'), 'demo_seat': seat, 'payload': payload,
    })
    body = resp.get_json()
    assert resp.status_code == 200 and body.get('success'), body
    return body

# 1) 选择前：两席都能看到共享奖励（拆分前基线）
run0 = get_run(0)
assert run0['state']['reward'] and 'rose' in run0['state']['reward']['cards'], '选前席0应见奖励'
run1 = get_run(1)
assert run1['state']['reward'] and 'basic' in run1['state']['reward']['cards'], '选前席1应见奖励'
print('[1] 拆分前两席均可见奖励 OK')

# 2) 席0领金币 + 选卡 + 继续（2026-10-13 口径：continue 才算完成）
act(0, {'_type': 'choose_reward', 'reward_type': 'gold'})
act(0, {'_type': 'choose_reward', 'reward_type': 'card', 'card_id': 'rose'})
act(0, {'_type': 'choose_reward', 'reward_type': 'continue'})
print('[2] 席0完成奖励选择 OK')

# 3) 【核心断言】席1读视角必须投影本席待选奖励（修复前这里是 None）
run1 = get_run(1)
proj = run1['state']['reward']
assert proj, 'BUG 复现：席1看不到待选奖励'
assert proj['gold'] == 30 and set(proj['cards']) == {'basic', 'rose'}
assert run1['coop_coord']['reward_pending_seats'] == [1]
print('[3] 席1读视角投影本席待选奖励 OK')

# 4) 已完成的席0读视角：无奖励 + 协调态显示等待席1
run0 = get_run(0)
assert run0['state']['reward'] is None
assert run0['coop_coord']['reward_pending_seats'] == [1]
print('[4] 席0等待视角（reward 空 + pending=[1]）OK')

# 5) 席1离场 → 全员完成，阶段推进回地图
body = act(1, {'_type': 'choose_reward', 'reward_type': 'leave'})
final = get_run(1)
assert final['coop_coord']['reward_pending_seats'] == []
assert final['state']['phase'] in ('map', 'reward'), final['state']['phase']
print(f"[5] 席1离场后全员完成，phase={final['state']['phase']} OK")

print('\n全部通过：奖励读视角投影 E2E 验证成功')
