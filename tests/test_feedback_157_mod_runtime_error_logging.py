"""反馈 #157/#162：玩家只看到「模组执行出现了一个意外错误」，管理员必须查得到原因。

ADMIN_EVENTS 是内存环形缓冲，进程重启即丢；重要事件（error/warning/mod_error）
现在同时写进 stdout，由 systemd 落盘到 journal。
"""

from pathlib import Path

import app


ROOT = Path(__file__).resolve().parents[1]


def test_durable_kinds_cover_mod_runtime_errors():
    assert 'mod_error' in app.ADMIN_EVENT_DURABLE_KINDS
    assert 'error' in app.ADMIN_EVENT_DURABLE_KINDS


def test_event_line_is_single_line_and_keeps_traceback_tail():
    traceback_text = '\n'.join(f'  line {index}' for index in range(1, 20))
    line = app.admin_event_log_line({
        'time': '2026-09-19T00:00:00',
        'kind': 'mod_error',
        'message': 'TypeError: bad step',
        'effect_type': 'damage',
        'card_id': 'Basic',
        'traceback': traceback_text,
    })

    assert line.startswith('[admin:mod_error] TypeError: bad step')
    assert 'effect_type=damage' in line
    assert 'card_id=Basic' in line
    assert '\n' not in line
    assert 'line 19' in line
    assert 'line 11' not in line


def test_admin_event_prints_durable_kinds_only(capsys):
    app.admin_event('mod_error', 'probe durable line', effect_type='damage')
    printed = capsys.readouterr().out
    assert '[admin:mod_error] probe durable line' in printed
    assert 'effect_type=damage' in printed

    app.admin_event('player', 'probe quiet line')
    assert 'probe quiet line' not in capsys.readouterr().out


def test_mod_runtime_error_logger_routes_to_admin_events():
    source = (ROOT / 'app.py').read_text(encoding='utf-8')
    assert "lambda message, **extra: admin_event('mod_error', message, **extra)" in source
