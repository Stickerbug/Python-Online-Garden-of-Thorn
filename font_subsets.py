import hashlib
import json
import os
import re
import threading
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Set

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(PROJECT_DIR, 'static', 'fonts')
COMMUNITY_FONT_DIR = os.path.join(FONTS_DIR, 'community')
COMMUNITY_FONT_URL_PREFIX = '/fonts/community'
BASE_REGULAR_TTF = os.path.join(FONTS_DIR, 'Kreadon-Regular.ttf')
BASE_REGULAR_SUBSET = os.path.join(FONTS_DIR, 'Kreadon-Regular.subset.woff2')

COMMUNITY_FONT_FAMILY = 'Kreadon Community'
MAX_REPORTED_CHARS = 80

_font_lock = threading.Lock()


def _decode_unicode_escapes(text: str) -> str:
    def repl_short(match):
        try:
            return chr(int(match.group(1), 16))
        except ValueError:
            return match.group(0)

    def repl_long(match):
        try:
            return chr(int(match.group(1), 16))
        except ValueError:
            return match.group(0)

    text = re.sub(r'\\u([0-9a-fA-F]{4})', repl_short, text)
    text = re.sub(r'\\U([0-9a-fA-F]{8})', repl_long, text)
    return text


def _skip_text_value(value: str) -> bool:
    text = value.strip()
    if not text:
        return True
    lowered = text.lower()
    if lowered.startswith('data:image/'):
        return True
    if lowered.startswith('/api/mod-assets/') or lowered.startswith('/static/assets/'):
        return True
    if len(text) > 4096 and re.fullmatch(r'[a-zA-Z0-9+/=\s:_;,.%-]+', text):
        return True
    return False


def _add_text_chars(chars: Set[str], text: str) -> None:
    if _skip_text_value(text):
        return
    chars.update(text)
    decoded = _decode_unicode_escapes(text)
    if decoded != text:
        chars.update(decoded)


def extract_visible_text_chars(data: Any) -> Set[str]:
    chars: Set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, str):
            _add_text_chars(chars, value)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key or '')
                if key_text in {'_image_data_url', '_package_sha256'}:
                    continue
                if key_text in {'image', 'image_url', 'asset_data', 'data_url'} and isinstance(item, str):
                    if _skip_text_value(item):
                        continue
                walk(item)

    walk(data)
    return {ch for ch in chars if _is_relevant_char(ch)}


def _is_relevant_char(ch: str) -> bool:
    if not ch or len(ch) != 1:
        return False
    cp = ord(ch)
    if cp in (0x0A, 0x0D, 0x09, 0x20):
        return False
    if cp < 0x20:
        return False
    return True


def _font_cache_key(path: str):
    try:
        stat = os.stat(path)
        return os.path.abspath(path), int(stat.st_mtime), int(stat.st_size)
    except OSError:
        return os.path.abspath(path), 0, 0


@lru_cache(maxsize=16)
def _font_cmap_cached(path: str, mtime: int, size: int) -> frozenset:
    if not os.path.exists(path):
        return frozenset()
    font = TTFont(path, lazy=True)
    try:
        cmap = set()
        for table in font['cmap'].tables:
            cmap.update(int(cp) for cp in table.cmap.keys())
        return frozenset(cmap)
    finally:
        font.close()


def font_cmap(path: str) -> Set[int]:
    path, mtime, size = _font_cache_key(path)
    return set(_font_cmap_cached(path, mtime, size))


def _safe_hash_key(value: str) -> str:
    text = re.sub(r'[^0-9a-fA-F]', '', str(value or '').lower())
    if len(text) >= 16:
        return text[:64]
    return hashlib.sha256(str(value or '').encode('utf-8')).hexdigest()


def _subset_font(input_path: str, output_path: str, chars: Iterable[str]) -> None:
    font = TTFont(input_path)
    try:
        options = Options()
        options.flavor = 'woff2'
        options.layout_features = ['*']
        options.name_IDs = ['*']
        options.legacy_cmap = True
        options.symbol_cmap = True
        options.drop_tables = ['DSIG', 'MVAR', 'cvar', 'fpgm', 'prep']
        options.hinting = True
        options.desubroutinize = True

        unicodes = {ord(ch) for ch in chars if _is_relevant_char(ch)}
        unicodes.add(0x0000)

        subsetter = Subsetter(options=options)
        subsetter.populate(unicodes=unicodes)
        subsetter.subset(font)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        font.save(output_path)
    finally:
        font.close()


def _chars_preview(chars: Iterable[str]) -> List[str]:
    ordered = sorted(set(chars), key=lambda ch: ord(ch))
    return ordered[:MAX_REPORTED_CHARS]


def community_font_report_for_data(data: Any, hash_key: str = '', generate: bool = False) -> Dict[str, Any]:
    return ensure_community_font_subset([data], hash_key=hash_key, generate=generate)


def ensure_community_font_subset(datas: Iterable[Any], hash_key: str = '', generate: bool = True) -> Dict[str, Any]:
    chars: Set[str] = set()
    for data in datas or []:
        chars.update(extract_visible_text_chars(data))

    base_cmap = font_cmap(BASE_REGULAR_SUBSET)
    full_cmap = font_cmap(BASE_REGULAR_TTF)
    needed = {ch for ch in chars if ord(ch) not in base_cmap}
    supported_missing = {ch for ch in needed if ord(ch) in full_cmap}
    unsupported = needed - supported_missing

    safe_hash = _safe_hash_key(hash_key or json.dumps(_chars_preview(chars), ensure_ascii=False, sort_keys=True))
    filename = f'Kreadon-community-{safe_hash[:16]}.woff2'
    output_path = os.path.join(COMMUNITY_FONT_DIR, filename)
    url = f'{COMMUNITY_FONT_URL_PREFIX}/{filename}?v={safe_hash[:16]}' if supported_missing else ''

    if generate and supported_missing and os.path.exists(BASE_REGULAR_TTF):
        with _font_lock:
            if not os.path.exists(output_path):
                _subset_font(BASE_REGULAR_TTF, output_path, supported_missing)

    warnings = []
    if supported_missing:
        warnings.append(
            f'社区模组包含 {len(supported_missing)} 个基础字体未覆盖字符，启用时会加载补充字体。'
        )
    if unsupported:
        warnings.append(
            f'Kreadon 字体不支持 {len(unsupported)} 个字符，浏览器会使用系统字体兜底。'
        )

    return {
        'success': True,
        'font_family': COMMUNITY_FONT_FAMILY,
        'hash': safe_hash,
        'url': url,
        'missing_count': len(supported_missing),
        'missing_chars': _chars_preview(supported_missing),
        'unsupported_count': len(unsupported),
        'unsupported_chars': _chars_preview(unsupported),
        'warnings': warnings,
        'generated': bool(generate and supported_missing and os.path.exists(output_path)),
    }
