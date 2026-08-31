import html
import re
import time
from collections import OrderedDict, deque
from threading import RLock


SUSPICIOUS_EVENTS = deque(maxlen=500)
_RATE_BUCKETS = OrderedDict()
_ILLEGAL_BUCKETS = OrderedDict()
_MUTES = OrderedDict()
_LOCK = RLock()

DEFAULT_ILLEGAL_LIMIT = 12
DEFAULT_ILLEGAL_WINDOW = 300
MAX_RATE_BUCKET_KEYS = 50_000
MAX_ILLEGAL_BUCKET_KEYS = 20_000
MAX_MUTE_KEYS = 20_000


def _now():
    return time.time()


def validate_int(value, *, default=None, minimum=None, maximum=None, name='value'):
    try:
        if isinstance(value, bool):
            raise ValueError
        parsed = int(value)
    except (TypeError, ValueError):
        if default is not None:
            return default
        raise ValueError(f'{name} must be an integer')
    if minimum is not None and parsed < minimum:
        raise ValueError(f'{name} must be >= {minimum}')
    if maximum is not None and parsed > maximum:
        raise ValueError(f'{name} must be <= {maximum}')
    return parsed


def validate_str(value, *, default='', min_len=0, max_len=256, pattern=None, name='value', strip=True, truncate=False):
    if value is None:
        text = default
    else:
        text = str(value)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    text = re.sub(r'[\r\n\t]+', ' ', text)
    if strip:
        text = text.strip()
    if len(text) < min_len:
        raise ValueError(f'{name} is too short')
    if len(text) > max_len and not truncate:
        raise ValueError(f'{name} is too long')
    if len(text) > max_len:
        text = text[:max_len]
    if pattern and not re.fullmatch(pattern, text):
        raise ValueError(f'{name} format is invalid')
    return text


def escape_text(value):
    return html.escape(str(value or ''), quote=False)


def rate_limiter(key, *, limit, window, now=None, consume=True):
    if not key:
        return False
    try:
        safe_limit = max(1, int(limit))
        safe_window = max(0.001, float(window))
    except (TypeError, ValueError):
        return False
    now = _now() if now is None else float(now)
    token = str(key)
    with _LOCK:
        bucket = _RATE_BUCKETS.get(token)
        if bucket is None:
            if not consume:
                return True
            bucket = deque()
            _RATE_BUCKETS[token] = bucket
        else:
            _RATE_BUCKETS.move_to_end(token)
        while bucket and now - bucket[0] >= safe_window:
            bucket.popleft()
        if not bucket and not consume:
            _RATE_BUCKETS.pop(token, None)
            return True
        allowed = len(bucket) < safe_limit
        if allowed and consume:
            bucket.append(now)
        while len(_RATE_BUCKETS) > MAX_RATE_BUCKET_KEYS:
            _RATE_BUCKETS.popitem(last=False)
        return allowed


def clear_rate_limit(key):
    if not key:
        return
    with _LOCK:
        _RATE_BUCKETS.pop(str(key), None)


def rate_limit_bucket_count():
    with _LOCK:
        return len(_RATE_BUCKETS)


def record_suspicious_event(kind, message, *, sid=None, user_id=None, ip=None, severity='medium', extra=None):
    event = {
        'ts': _now(),
        'kind': str(kind or 'unknown')[:64],
        'message': str(message or '')[:500],
        'sid': str(sid or '')[:80],
        'user_id': user_id,
        'ip': str(ip or '')[:80],
        'severity': str(severity or 'medium')[:24],
        'extra': dict(extra or {}),
    }
    with _LOCK:
        SUSPICIOUS_EVENTS.appendleft(event)
    return event


def recent_suspicious_events(limit=100):
    try:
        safe_limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        safe_limit = 100
    with _LOCK:
        return [dict(item) for item in list(SUSPICIOUS_EVENTS)[:safe_limit]]


def is_muted(identifier):
    if identifier is None:
        return False
    key = str(identifier)
    now = _now()
    with _LOCK:
        until = float(_MUTES.get(key) or 0)
        if until and until <= now:
            _MUTES.pop(key, None)
            return False
        if until:
            _MUTES.move_to_end(key)
        return bool(until and until > now)


def mute_remaining_seconds(identifier):
    if identifier is None:
        return 0
    key = str(identifier)
    now = _now()
    with _LOCK:
        until = float(_MUTES.get(key) or 0)
        if until and until <= now:
            _MUTES.pop(key, None)
            return 0
        if until:
            _MUTES.move_to_end(key)
        return max(0, int(round(until - now))) if until else 0


def mute_user(identifier, seconds=600, reason=''):
    if identifier is None:
        return None
    try:
        duration = max(1, int(seconds))
    except (TypeError, ValueError):
        duration = 600
    until = _now() + duration
    key = str(identifier)
    with _LOCK:
        _MUTES[key] = until
        _MUTES.move_to_end(key)
        while len(_MUTES) > MAX_MUTE_KEYS:
            _MUTES.popitem(last=False)
    record_suspicious_event('mute', f'muted {key}: {reason}', user_id=identifier if str(identifier).isdigit() else None)
    return until


def illegal_operation_key(sid=None, user_id=None):
    return f'user:{user_id}' if user_id else f'sid:{sid}'


def record_illegal_operation(key, *, limit=DEFAULT_ILLEGAL_LIMIT, window=DEFAULT_ILLEGAL_WINDOW):
    if not key:
        return 0, False
    now = _now()
    token = str(key)
    with _LOCK:
        bucket = _ILLEGAL_BUCKETS.get(token)
        if bucket is None:
            bucket = deque()
            _ILLEGAL_BUCKETS[token] = bucket
        else:
            _ILLEGAL_BUCKETS.move_to_end(token)
        while bucket and now - bucket[0] >= window:
            bucket.popleft()
        bucket.append(now)
        count = len(bucket)
        while len(_ILLEGAL_BUCKETS) > MAX_ILLEGAL_BUCKET_KEYS:
            _ILLEGAL_BUCKETS.popitem(last=False)
    return count, count >= limit


def reset_illegal_operations(key):
    if not key:
        return
    with _LOCK:
        _ILLEGAL_BUCKETS.pop(str(key), None)
