"""把低频重读挪出 eventlet 事件循环的契约（单进程 hub 不能被慢查询按住）。"""

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_PY = (ROOT / 'app.py').read_text(encoding='utf-8')


def _normalized(source):
    return re.sub(r'\s+', ' ', source)


def test_heavy_admin_reads_run_in_the_thread_pool():
    normalized = _normalized(APP_PY)
    assert 'def run_off_event_loop(fn, *args, **kwargs):' in APP_PY
    assert 'run_off_event_loop( search_handling_matches,' in normalized
    assert 'run_off_event_loop( list_average_round_stats,' in normalized
    assert 'run_off_event_loop(build_replay_download_package, replay_id)' in normalized


def test_off_loop_helper_executes_the_callable():
    import app as gtn

    assert gtn.run_off_event_loop(lambda value: value + 1, 41) == 42
