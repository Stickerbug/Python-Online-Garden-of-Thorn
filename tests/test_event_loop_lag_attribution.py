"""事件循环卡顿要有归因：看门狗告警必须写明「当时在跑什么」，并且能在 health 里看到。

背景：单进程 eventlet 里，任何一个在循环里跑的慢活都会让别人的 socket 动作排队，
客户端 6 秒超时弹「服务器没有响应」。此前只有一句 lag 数字，无法归因。
"""

import time

import app


def _reset_activity():
    app._CURRENT_ACTIVITY.update({'label': '', 'started': 0.0, 'depth': 0})
    app._ACTIVITY_RECENT.clear()


def test_activity_scope_labels_nested_work_and_restores_state():
    _reset_activity()
    with app.activity_scope('socket:play_card'):
        assert app.current_activity_snapshot()['label'] == 'socket:play_card'
        started = app._CURRENT_ACTIVITY['started']
        with app.activity_scope('inner:step'):
            # 内层不再重置起点，保持「这一段整体跑了多久」
            assert app._CURRENT_ACTIVITY['started'] == started
            assert app._CURRENT_ACTIVITY['depth'] == 2
        assert app._CURRENT_ACTIVITY['depth'] == 1
        assert app.current_activity_snapshot()['label'] == 'socket:play_card'
    snapshot = app.current_activity_snapshot()
    assert snapshot['label'] == 'idle'
    assert snapshot['running_ms'] == 0.0
    assert app._CURRENT_ACTIVITY['depth'] == 0


def test_slow_activity_is_recorded_for_the_watchdog():
    _reset_activity()
    with app.activity_scope('http:POST /api/story/run/action'):
        time.sleep(0.05)
        app._ACTIVITY_SLOW_MS = 1.0
    recent = app.current_activity_snapshot()['recent_slow']
    assert recent and recent[-1]['label'] == 'http:POST /api/story/run/action'
    assert recent[-1]['ms'] >= 1.0
    app._ACTIVITY_SLOW_MS = 300


def test_loop_lag_health_payload_reports_samples_and_last_warning():
    app.EVENT_LOOP_LAG_SAMPLES.clear()
    app.record_event_loop_lag(120)
    app.record_event_loop_lag(2500)
    app._LAST_LOOP_LAG_EVENT.clear()
    app._LAST_LOOP_LAG_EVENT.update({'ts': '2026-09-19T00:00:00Z', 'lag_ms': 4200.0, 'activity': 'socket:play_card'})

    payload = app.loop_lag_health_payload()

    assert payload['samples'] == 2
    assert payload['max_ms'] == 2500
    assert payload['last_warning']['activity'] == 'socket:play_card'
    app.EVENT_LOOP_LAG_SAMPLES.clear()
    app._LAST_LOOP_LAG_EVENT.clear()


def test_socket_and_http_work_is_attributed():
    source = (app.__file__ or '')
    with open(source, encoding='utf-8') as handle:
        text = handle.read()
    # socket 动作带标签
    assert "with activity_scope(f'socket:{event_name}'):" in text
    # HTTP 请求带标签，并在 teardown 释放
    assert "scope = activity_scope(f'http:{request.method} {request.path}')" in text
    assert 'def end_request_activity_scope(_exc=None):' in text
    # 看门狗告警带归因，且 kind 会落进 journal
    assert "'suspicious'," in text
    assert 'suspicious' in app.ADMIN_EVENT_DURABLE_KINDS
    assert 'loop_lag_health_payload()' in text
    assert "'current_activity': current_activity_snapshot()," in text
