# -*- coding: utf-8 -*-
"""GB-387/392：日志重写代数与增量下发。

服务端压缩战报会在**行数不变**时重写同位置的行（使用轻×3 → ×4），
仅按行数切片会把内容替换当成「无新行」，客户端累积器保留旧行后被
显示层继续合并，表现为 1,2,8,64 的指数计数。修复：引擎维护重写代数，
切片按（代数, 行数）记账，代数变化整体重发。
"""

import app as gtn
from game_engine import GameEngine


class FakeRoom:
    pass


def _engine_with_repeated_plays(times=4):
    engine = GameEngine()
    for play in range(1, times + 1):
        engine.log_msg('玩家1使用轻，玩家2受到2D×2（H=30→28→26）')
    return engine


def test_pure_append_does_not_bump_generation():
    engine = GameEngine()
    engine.log_msg('普通行A')
    engine.log_msg('普通行B')
    assert engine._log_rewrite_generation == 0


def test_merge_rewrite_bumps_generation():
    engine = _engine_with_repeated_plays(4)
    # 同一行被反复合并重写：行数保持 1，代数持续增长。
    assert len(engine.log) == 1
    assert engine._log_rewrite_generation >= 3


def test_slice_resends_full_log_when_generation_changes():
    engine = _engine_with_repeated_plays(3)
    state_one = {'log': list(engine.log), 'log_start': 0}
    gtn._slice_state_log_for_recipient(state_one, engine, 'p:1')
    assert state_one['log'] == engine.log  # 首发全量
    gen_seen = state_one['log_gen']

    # 第 4 打：压缩重写 ×3 → ×4（行数不变、代数 +1）→ 必须整体重发。
    engine.log_msg('玩家1使用轻，玩家2受到2D×2（H=30→28→26）')
    state_two = {'log': list(engine.log), 'log_start': 0}
    gtn._slice_state_log_for_recipient(state_two, engine, 'p:1')
    assert state_two['log'] == engine.log
    assert state_two['log_gen'] == engine._log_rewrite_generation
    assert state_two['log_gen'] > gen_seen


def test_slice_sends_delta_when_generation_stable():
    engine = GameEngine()
    engine.log_msg('行1')
    first = {'log': list(engine.log), 'log_start': 0}
    gtn._slice_state_log_for_recipient(first, engine, 'p:2')
    assert first['log'] == ['行1']

    # 纯追加（代数不变）：只发新增行。
    engine.log_msg('行2')
    second = {'log': list(engine.log), 'log_start': 0}
    gtn._slice_state_log_for_recipient(second, engine, 'p:2')
    assert second['log'] == ['行2']
    assert second['log_start'] == 1


def test_slice_resets_cursor_after_full_resend():
    """整体重发后记账重置：后续纯追加按新游标增量，不会误发空增量。"""
    engine = _engine_with_repeated_plays(2)
    state = {'log': list(engine.log), 'log_start': 0}
    gtn._slice_state_log_for_recipient(state, engine, 'p:3')

    engine.log_msg('玩家1使用轻，玩家2受到2D×2（H=30→28→26）')  # ×2 → ×3 重写
    state = {'log': list(engine.log), 'log_start': 0}
    gtn._slice_state_log_for_recipient(state, engine, 'p:3')
    assert state['log'] == engine.log  # 重写后全量

    engine.log_msg('新追加行')  # 纯追加：代数不变
    engine.log.append('直接追加行')  # 再追加一条
    state = {'log': list(engine.log), 'log_start': 0}
    gtn._slice_state_log_for_recipient(state, engine, 'p:3')
    # 重发时游标记在压缩行（1 行）之后：两条新行都属于增量。
    assert state['log'] == ['新追加行', '直接追加行']
    assert state['log_start'] == 1
