import json
import os
import re
import time
import unicodedata


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RULES_PATH = os.path.join(BASE_DIR, 'static', 'data', 'moderation_rules.json')

REPORT_CATEGORIES = {
    'chat_message': {'abusive_language', 'sexual_content', 'spam', 'privacy_leak', 'harassment', 'other'},
    'player': {'cheating', 'smurfing', 'boosting', 'stalling', 'inappropriate_name', 'harassment', 'other'},
    'match': {'cheating', 'bug_abuse', 'boosting', 'stalling', 'abnormal_match', 'other'},
    'replay': {'cheating', 'bug_abuse', 'boosting', 'stalling', 'abnormal_match', 'other'},
    'mod': {'malicious_mod', 'stolen_content', 'offensive_content', 'bug_abuse', 'other'},
}

VALID_REPORT_OBJECT_TYPES = set(REPORT_CATEGORIES)
VALID_REPORT_ACTIONS = {'accept', 'reject', 'abusive'}
VALID_MODERATION_ACTIONS = {'none', 'warn', 'mute', 'ban', 'invalidate_match'}

_RULE_CACHE = None
_RULE_CACHE_MTIME = None

ACTION_BY_LEVEL = {
    0: 'allow',
    1: 'allow_log',
    2: 'allow_flag',
    3: 'mask_flag',
    4: 'reject_mute',
}

NICKNAME_BLOCK_LEVEL = 3
GUEST_NICKNAME_BLOCK_LEVEL = 2
NICKNAME_ALWAYS_BLOCK_CATEGORIES = {'sexual', 'political'}

_RESERVED_LONG_NICKNAMES = ('phelren', 'stickerbug', 'netherdog')
_RESERVED_NICKNAME_DISPLAY = {
    'phelren': 'Phelren',
    'stickerbug': 'Stickerbug',
    'netherdog': 'NetherDog',
    'eric': 'Eric',
}
_NICKNAME_CHAR_EQUIVALENTS = {
    '0': {'o'},
    '1': {'i', 'l'},
    '2': {'r'},
    '3': {'e'},
    '4': {'a', 'h'},
    '5': {'s'},
    '6': {'b', 'g'},
    '7': {'t'},
    '8': {'b'},
    '9': {'g'},
    'ρ': {'p'},
    'р': {'p'},
    'þ': {'p'},
    'һ': {'h'},
    'н': {'h'},
    'е': {'e'},
    'ε': {'e'},
    'ӏ': {'i', 'l'},
    'і': {'i', 'l'},
    'ι': {'i', 'l'},
    'ł': {'l'},
    'г': {'r'},
    'я': {'r'},
    'ո': {'n'},
    'η': {'n'},
    'п': {'n'},
    'ѕ': {'s'},
    'т': {'t'},
    'τ': {'t'},
    'с': {'c'},
    'κ': {'k'},
    'к': {'k'},
    'в': {'b'},
    'υ': {'u'},
    'ԍ': {'g'},
    'ց': {'g'},
    'ԁ': {'d'},
    'ο': {'o'},
    'о': {'o'},
}
_ERIC_DECORATION_TOKENS = (
    'administrator', 'developer', 'official', 'oficial', 'admin', 'player', 'real',
    'the', 'its', 'iam', 'im', 'dev', 'gtn', 'mr', 'ai', 'bot', 'user',
    'true', 'x', 'v', '官方', '管理员', '管理', '开发者', '开发', '本人', '真的',
)

_CONTROL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')
_REPEAT_RE = re.compile(r'(.)\1{2,}')


def _nickname_identity_text(text):
    value = unicodedata.normalize('NFKC', str(text or '')).casefold()
    value = unicodedata.normalize('NFKD', value)
    compact = []
    for ch in value:
        category = unicodedata.category(ch)
        if category.startswith('M') or not ch.isalnum():
            continue
        if compact and compact[-1] == ch:
            continue
        compact.append(ch)
    return ''.join(compact)


def _nickname_chars_equal(actual, expected):
    return actual == expected or expected in _NICKNAME_CHAR_EQUIVALENTS.get(actual, set())


def _nickname_edit_distance(actual, expected, limit=1):
    if abs(len(actual) - len(expected)) > limit:
        return limit + 1
    rows = [[0] * (len(expected) + 1) for _ in range(len(actual) + 1)]
    for i in range(len(actual) + 1):
        rows[i][0] = i
    for j in range(len(expected) + 1):
        rows[0][j] = j
    for i in range(1, len(actual) + 1):
        for j in range(1, len(expected) + 1):
            substitution = 0 if _nickname_chars_equal(actual[i - 1], expected[j - 1]) else 1
            rows[i][j] = min(
                rows[i - 1][j] + 1,
                rows[i][j - 1] + 1,
                rows[i - 1][j - 1] + substitution,
            )
            if (
                i > 1
                and j > 1
                and _nickname_chars_equal(actual[i - 1], expected[j - 2])
                and _nickname_chars_equal(actual[i - 2], expected[j - 1])
            ):
                rows[i][j] = min(rows[i][j], rows[i - 2][j - 2] + 1)
    return rows[-1][-1]


def _matches_long_reserved_nickname(compact, target):
    shortest = max(1, len(target) - 1)
    longest = len(target) + 1
    for start in range(len(compact)):
        for size in range(shortest, longest + 1):
            end = start + size
            if end > len(compact):
                continue
            if _nickname_edit_distance(compact[start:end], target, limit=1) <= 1:
                return True
    return False


def _is_eric_decoration(value):
    if not value:
        return True
    reachable = {0}
    for index in range(len(value) + 1):
        if index not in reachable:
            continue
        if index < len(value) and value[index].isdigit():
            reachable.add(index + 1)
        for token in _ERIC_DECORATION_TOKENS:
            if value.startswith(token, index):
                reachable.add(index + len(token))
    return len(value) in reachable


def _matches_reserved_eric(compact):
    target = 'eric'
    for start in range(max(0, len(compact) - len(target)) + 1):
        end = start + len(target)
        if end > len(compact):
            continue
        segment = compact[start:end]
        if not all(_nickname_chars_equal(ch, target[index]) for index, ch in enumerate(segment)):
            continue
        if _is_eric_decoration(compact[:start]) and _is_eric_decoration(compact[end:]):
            return True
    return False


def match_reserved_nickname(text):
    compact = _nickname_identity_text(text)
    if not compact:
        return None
    for target in _RESERVED_LONG_NICKNAMES:
        if _matches_long_reserved_nickname(compact, target):
            return _RESERVED_NICKNAME_DISPLAY[target]
    if _matches_reserved_eric(compact):
        return _RESERVED_NICKNAME_DISPLAY['eric']
    return None


def normalize_message(text):
    value = str(text or '')
    value = unicodedata.normalize('NFKC', value).casefold()
    value = _CONTROL_RE.sub('', value)
    kept = []
    for ch in value:
        category = unicodedata.category(ch)
        if category[0] in {'P', 'Z'}:
            continue
        kept.append(ch)
    value = ''.join(kept)
    value = _REPEAT_RE.sub(r'\1\1', value)
    return value.strip()


def _default_rules():
    return {
        'schema_version': 1,
        'actions': ACTION_BY_LEVEL,
        'allowlist': [],
        'rules': [
            {'id': 'xss_tag', 'type': 'regex', 'target': 'raw', 'pattern': r'<\s*/?\s*(script|iframe|object|embed|svg)\b[^>]*>', 'level': 3, 'action': 'mask_flag'},
            {'id': 'xss_js_url', 'type': 'regex', 'target': 'raw', 'pattern': r'javascript\s*:', 'level': 3, 'action': 'mask_flag'},
            {'id': 'phone_privacy', 'type': 'regex', 'target': 'raw', 'pattern': r'(?<!\d)1[3-9]\d{9}(?!\d)', 'level': 3, 'action': 'mask_flag'},
            {'id': 'contact_privacy_hint', 'type': 'regex', 'target': 'raw', 'pattern': r'(qq|vx|微信|手机号)\s*[:：]?\s*[0-9A-Za-z_\-]{5,}', 'level': 2, 'action': 'allow_flag'},
            {'id': 'death_harassment_cn', 'type': 'contains', 'target': 'normalized', 'pattern': '去死', 'level': 3, 'action': 'mask_flag'},
            {'id': 'self_harm_cn', 'type': 'contains', 'target': 'normalized', 'pattern': '自杀', 'level': 2, 'action': 'allow_flag'},
            {'id': 'spam_url', 'type': 'regex', 'target': 'raw', 'pattern': r'(https?://|www\.)\S{8,}', 'level': 2, 'action': 'allow_flag'},
            {'id': 'repeated_chars', 'type': 'regex', 'target': 'raw', 'pattern': r'(.)(\1){9,}', 'level': 1, 'action': 'allow_log'},
        ],
        'reject_rules': [
            {'id': 'massive_mention_spam', 'type': 'regex', 'target': 'raw', 'pattern': r'(@\S+\s*){8,}', 'level': 4, 'action': 'reject_mute'},
        ],
    }


def _load_rules():
    global _RULE_CACHE, _RULE_CACHE_MTIME
    path = os.environ.get('GTN_MODERATION_RULES_PATH', DEFAULT_RULES_PATH)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = None
    if _RULE_CACHE is not None and _RULE_CACHE_MTIME == mtime:
        return _RULE_CACHE
    data = _default_rules()
    if mtime is not None:
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                data['schema_version'] = loaded.get('schema_version') or data['schema_version']
                data['actions'] = loaded.get('actions') or data['actions']
                data['allowlist'] = list(loaded.get('allowlist') or data.get('allowlist') or [])
                data['rules'] = list(loaded.get('rules') or data['rules'])
                data['reject_rules'] = list(loaded.get('reject_rules') or data.get('reject_rules') or [])
        except Exception:
            pass
    data['_allowlist_normalized'] = {
        normalize_message(term)
        for term in data.get('allowlist') or []
        if normalize_message(term)
    }
    for rule in list(data.get('rules') or []) + list(data.get('reject_rules') or []):
        if not isinstance(rule, dict):
            continue
        terms = rule.get('terms')
        if isinstance(terms, list):
            rule['_normalized_terms'] = [
                normalize_message(term)
                for term in terms
                if isinstance(term, str) and normalize_message(term)
            ]
    _RULE_CACHE = data
    _RULE_CACHE_MTIME = mtime
    return data


def _rule_level(rule):
    try:
        return max(0, min(int(rule.get('level', rule.get('risk', 1)) or 1), 4))
    except (TypeError, ValueError):
        return 1


def _rule_action(rule, level):
    action = str(rule.get('action') or '').strip()
    return action or ACTION_BY_LEVEL.get(level, 'allow_log')


def _rule_target_text(rule, raw_text, normalized_text):
    target = str(rule.get('target') or 'normalized').lower()
    if target in {'raw', 'raw_lower'}:
        return raw_text.casefold()
    return normalized_text


def _rule_matches(rule, raw_text, normalized_text, allowlist):
    pattern = str(rule.get('pattern') or '')
    rtype = str(rule.get('type') or 'contains').lower()
    target_text = _rule_target_text(rule, raw_text, normalized_text)
    if rtype in {'term_list', 'terms'}:
        matched = []
        for term in rule.get('_normalized_terms') or []:
            if term in allowlist:
                continue
            if term and term in normalized_text:
                matched.append(term)
                if len(matched) >= 8:
                    break
        return matched
    if rtype == 'domain_list':
        raw_lower = raw_text.casefold()
        matched = []
        for term in rule.get('terms') or []:
            term = str(term or '').strip().casefold()
            if len(term) >= 4 and term in raw_lower:
                matched.append(term)
                if len(matched) >= 8:
                    break
        return matched
    if not pattern:
        return []
    if rtype == 'regex':
        try:
            return [pattern] if re.search(pattern, target_text, flags=re.IGNORECASE) is not None else []
        except re.error:
            return []
    normalized_pattern = normalize_message(pattern)
    if normalized_pattern in allowlist:
        return []
    return [pattern] if normalized_pattern and normalized_pattern in target_text else []


def _mask_by_rule(text, rule, matched_terms=None):
    pattern = str(rule.get('pattern') or '')
    if str(rule.get('type') or 'contains').lower() == 'regex':
        if not pattern:
            return text
        try:
            return re.sub(pattern, '***', text, flags=re.IGNORECASE)
        except re.error:
            return text
    masked = text
    for term in list(matched_terms or []):
        if len(str(term)) < 2:
            continue
        masked = re.sub(re.escape(str(term)), '***', masked, flags=re.IGNORECASE)
    if pattern:
        masked = re.sub(re.escape(pattern), '***', masked, flags=re.IGNORECASE)
    return masked


def check_message_risk(text):
    raw_text = str(text or '')
    normalized = normalize_message(raw_text)
    risk_level = 0
    action = 'allow'
    matched = []
    sanitized = raw_text
    rules_data = _load_rules()
    allowlist = set(rules_data.get('_allowlist_normalized') or set())
    for rule in list(rules_data.get('rules') or []) + list(rules_data.get('reject_rules') or []):
        if not isinstance(rule, dict):
            continue
        matched_terms = _rule_matches(rule, raw_text, normalized, allowlist)
        if not matched_terms:
            continue
        level = _rule_level(rule)
        if level > risk_level:
            risk_level = level
            action = _rule_action(rule, level)
        matched.append({
            'id': str(rule.get('id') or rule.get('pattern') or 'rule')[:120],
            'category': str(rule.get('category') or '').strip().lower()[:80],
            'level': level,
            'action': _rule_action(rule, level),
            'matches': [str(term)[:80] for term in matched_terms[:5]],
        })
        if level >= 3 or rule.get('mask'):
            sanitized = _mask_by_rule(sanitized, rule, matched_terms)
    return {
        'risk_level': risk_level,
        'action': action,
        'matched_rules': matched,
        'sanitized_text': sanitized,
        'normalized_message': normalized,
        'checked_at': int(time.time()),
    }


def check_nickname_risk(text, guest=False):
    """Apply the shared chat rules with stricter, nickname-specific thresholds."""
    result = check_message_risk(text)
    reserved_name = match_reserved_nickname(text)
    if reserved_name:
        result['risk_level'] = max(4, int(result.get('risk_level') or 0))
        result['action'] = 'reject_nickname'
        result['matched_rules'] = list(result.get('matched_rules') or []) + [{
            'id': f'reserved_nickname_{reserved_name.casefold()}',
            'category': 'reserved_identity',
            'level': 4,
            'action': 'reject_nickname',
            'matches': [reserved_name],
        }]
    threshold = GUEST_NICKNAME_BLOCK_LEVEL if guest else NICKNAME_BLOCK_LEVEL
    matched_categories = {
        str(item.get('category') or '').strip().lower()
        for item in result.get('matched_rules') or []
        if isinstance(item, dict)
    }
    blocked = (
        bool(reserved_name)
        or
        int(result.get('risk_level') or 0) >= threshold
        or bool(matched_categories & NICKNAME_ALWAYS_BLOCK_CATEGORIES)
    )
    return {
        **result,
        'blocked': blocked,
        'threshold': threshold,
        'matched_categories': sorted(category for category in matched_categories if category),
        'reserved_name': reserved_name,
    }


def report_category_allowed(object_type, category):
    return str(category or '') in REPORT_CATEGORIES.get(str(object_type or ''), set())
