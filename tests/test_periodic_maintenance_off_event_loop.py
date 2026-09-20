"""周期性维护不能在事件循环里跑：它正是「每 10 分钟卡 18 秒」的来源。

线上看门狗（2026-09-20 部署后）记录到 17078 / 18169 / 18117 / 18072 / 18168 / 18649 ms
六次卡顿，间隔正好 10 分 19 秒 —— 对应 ``_friend_request_cleanup_worker`` 的 600 秒周期里
那批全库维护（``recover_reputation_daily`` 会遍历所有账号，1.16GB 库上要十几秒）。
这个测试守住「这批重活必须经 ``run_off_event_loop``」。
"""

from pathlib import Path

import app


APP_PY = (Path(app.__file__).resolve()).read_text(encoding='utf-8')


def _function_source(name: str, next_name: str) -> str:
    body = APP_PY.split(f'def {name}(', 1)[1].split(f'def {next_name}(', 1)[0]
    return f'def {name}({body}'


def test_friend_request_cleanup_moves_bulk_work_to_the_thread_pool():
    worker = _function_source('_friend_request_cleanup_worker', '_account_integrity_maintenance_once')
    assert 'run_off_event_loop(_account_integrity_maintenance_once)' in worker
    # 会发 websocket 的那一支留在绿色线程里
    assert 'refresh_online_reputation()' in worker


def test_bulk_maintenance_helper_keeps_the_original_operations():
    helper = _function_source('_account_integrity_maintenance_once', 'ensure_friend_request_cleanup_started')
    for call in (
        'account_integrity.recover_reputation_daily()',
        'account_integrity.expire_team_reports()',
        'account_integrity.refresh_recent_account_links()',
        'cleanup_expired_friend_requests_once(force=True)',
        'cleanup_expired_content_disables_once()',
    ):
        assert call in helper


def test_dm_cleanup_also_runs_off_the_event_loop():
    worker = _function_source('_dm_cleanup_worker', 'ensure_dm_cleanup_started')
    assert 'run_off_event_loop(cleanup_old_dm_messages_once)' in worker
