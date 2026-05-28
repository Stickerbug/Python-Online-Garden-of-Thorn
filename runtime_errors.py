from __future__ import annotations

import traceback
from typing import Callable, Optional


MOD_RUNTIME_ERROR_MESSAGE = '模组执行出现了一个意外错误。请联系管理员。'

_logger: Optional[Callable[..., None]] = None


def set_mod_runtime_error_logger(logger: Optional[Callable[..., None]]) -> None:
    global _logger
    _logger = logger


def record_mod_runtime_error(message: str, **extra) -> None:
    if _logger is None:
        return
    payload = dict(extra)
    payload.setdefault('traceback', traceback.format_exc())
    try:
        _logger(str(message), **payload)
    except Exception:
        pass
