import colorsys
import hashlib
import json
import re


TITLE_STYLE_VERSION = 1
TITLE_STYLE_MAX_SEGMENTS = 24
TITLE_STYLE_MAX_TEXT = 64
TITLE_STYLE_SEGMENT_ID_RE = re.compile(r'^[a-zA-Z0-9_.:-]{1,40}$')

TITLE_COLOR_TOKENS = (
    'thorn', 'bloom', 'root', 'guard', 'curse', 'infect',
    'health', 'elixir', 'energy', 'magic', 'damage', 'electric', 'poison', 'fire', 'armor',
    'precision', 'banish', 'indestructible', 'critical',
    'primary', 'common', 'unusual', 'rare', 'epic', 'legendary', 'mythic',
    'ultra', 'super', 'omega', 'eternal', 'unique',
    'milestone', 'hidden', 'admin', 'neutral', 'spectator',
)

RAINBOW_STOPS = (
    '#FF3B30', '#FF9500', '#FFCC00', '#34C759',
    '#00B7C7', '#3478F6', '#7857D8', '#FF2D96',
)


def _alpha_byte(value):
    text = str(value or '').strip().rstrip('%')
    if not text:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    if '%' in str(value):
        number /= 100.0
    elif number > 1:
        number /= 100.0
    if not 0 <= number <= 1:
        return None
    return round(number * 255)


def normalize_title_color(value, fallback=None):
    """Normalize a safe title color token or concrete color value."""
    text = str(value or '').strip()
    lowered = text.lower()
    if lowered in TITLE_COLOR_TOKENS:
        return lowered

    alpha = None
    color_text = text
    alpha_match = re.fullmatch(r'(.+?)@([0-9]+(?:\.[0-9]+)?%?)', text)
    if alpha_match:
        color_text = alpha_match.group(1).strip()
        alpha = _alpha_byte(alpha_match.group(2))
        if alpha is None:
            return fallback
        lowered = color_text.lower()

    short_hex = re.fullmatch(r'#([0-9a-fA-F]{3})([0-9a-fA-F])?', color_text)
    if short_hex:
        digits = ''.join(ch * 2 for ch in short_hex.group(1))
        embedded_alpha = short_hex.group(2)
        if alpha is None and embedded_alpha:
            alpha = int(embedded_alpha * 2, 16)
        return f'#{digits.upper()}' + (f'{alpha:02X}' if alpha is not None else '')

    full_hex = re.fullmatch(r'#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?', color_text)
    if full_hex:
        digits = full_hex.group(1).upper()
        embedded_alpha = full_hex.group(2)
        if alpha is None and embedded_alpha:
            alpha = int(embedded_alpha, 16)
        return f'#{digits}' + (f'{alpha:02X}' if alpha is not None else '')

    rgb_match = re.fullmatch(
        r'rgba?\s*\(\s*(\d{1,3})\s*[,;/]\s*(\d{1,3})\s*[,;/]\s*(\d{1,3})'
        r'(?:\s*[,;/]\s*([0-9]+(?:\.[0-9]+)?%?))?\s*\)',
        lowered,
    )
    if rgb_match:
        channels = [int(rgb_match.group(index)) for index in range(1, 4)]
        if not all(0 <= channel <= 255 for channel in channels):
            return fallback
        if alpha is None and rgb_match.group(4) is not None:
            alpha = _alpha_byte(rgb_match.group(4))
            if alpha is None:
                return fallback
        result = '#{:02X}{:02X}{:02X}'.format(*channels)
        return result + (f'{alpha:02X}' if alpha is not None else '')

    hsv_match = re.fullmatch(
        r'hsva?\s*\(\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))'
        r'\s*[,;/]\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))%?'
        r'\s*[,;/]\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))%?'
        r'(?:\s*[,;/]\s*([0-9]+(?:\.[0-9]+)?%?))?\s*\)',
        lowered,
    )
    if hsv_match:
        hue = float(hsv_match.group(1)) % 360.0
        saturation = float(hsv_match.group(2))
        value_level = float(hsv_match.group(3))
        if saturation > 1:
            saturation /= 100.0
        if value_level > 1:
            value_level /= 100.0
        if not (0 <= saturation <= 1 and 0 <= value_level <= 1):
            return fallback
        if alpha is None and hsv_match.group(4) is not None:
            alpha = _alpha_byte(hsv_match.group(4))
            if alpha is None:
                return fallback
        red, green, blue = colorsys.hsv_to_rgb(hue / 360.0, saturation, value_level)
        result = '#{:02X}{:02X}{:02X}'.format(
            round(red * 255), round(green * 255), round(blue * 255),
        )
        return result + (f'{alpha:02X}' if alpha is not None else '')
    return fallback


def _normalize_angle(value, default=90):
    text = str(value or '').strip().lower().removesuffix('deg')
    try:
        angle = float(text)
    except (TypeError, ValueError):
        return default
    if not -3600 <= angle <= 3600:
        return default
    return round(angle % 360, 3)


def _solid_paint(value):
    color = normalize_title_color(value)
    if not color:
        raise ValueError(f'无法识别称号颜色：{value}')
    return {'kind': 'solid', 'color': color}


def _parse_gradient(value):
    raw = str(value or '').strip()
    angle = 90
    stops_text = raw
    if ',' in raw:
        first, remainder = raw.split(',', 1)
        if re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)\s*(?:deg)?', first.strip(), re.I):
            angle = _normalize_angle(first)
            stops_text = remainder
    stops = [normalize_title_color(item.strip()) for item in stops_text.split('>')]
    if len(stops) < 2 or any(not item for item in stops):
        raise ValueError('渐变至少需要两个有效颜色，并使用 > 分隔')
    if len(stops) > 12:
        raise ValueError('单段渐变最多包含12个颜色')
    return {'kind': 'gradient', 'angle': angle, 'colors': stops}


def _parse_theme(value):
    branches = {}
    for item in str(value or '').split(';'):
        key, sep, branch_value = item.partition('=')
        if sep:
            branches[key.strip().lower()] = branch_value.strip()
    if set(branches) != {'light', 'dark'}:
        raise ValueError('主题色应写为 light=颜色;dark=颜色')
    return {
        'kind': 'theme',
        'light': _solid_paint(branches['light']),
        'dark': _solid_paint(branches['dark']),
    }


def _parse_paint_tag(tag):
    raw = str(tag or '').strip()
    lowered = raw.lower()
    if lowered == 'rainbow':
        return {'kind': 'rainbow', 'angle': 90, 'colors': list(RAINBOW_STOPS)}
    if lowered.startswith('rainbow:'):
        return {
            'kind': 'rainbow',
            'angle': _normalize_angle(raw.split(':', 1)[1]),
            'colors': list(RAINBOW_STOPS),
        }
    kind, sep, value = raw.partition(':')
    if not sep:
        raise ValueError(f'未知称号样式：{raw}')
    kind = kind.strip().lower()
    if kind in {'color', 'solid'}:
        return _solid_paint(value)
    if kind in {'gradient', 'grad'}:
        return _parse_gradient(value)
    if kind == 'theme':
        return _parse_theme(value)
    raise ValueError(f'未知称号样式：{kind}')


def _segment_id(index, text, paint, explicit=''):
    if explicit:
        if not TITLE_STYLE_SEGMENT_ID_RE.fullmatch(explicit):
            raise ValueError('样式段 ID 仅可包含字母、数字及 . _ : -')
        return explicit
    digest = hashlib.sha1(
        f'{index}\0{text}\0{json.dumps(paint, ensure_ascii=False, sort_keys=True)}'.encode('utf-8')
    ).hexdigest()[:8]
    return f's{index + 1}-{digest}'


def _make_segment(index, text, paint, explicit_id=''):
    if not text:
        raise ValueError('称号样式段不能为空')
    return {
        'id': _segment_id(index, text, paint, explicit=explicit_id),
        'text': text,
        'paint': paint,
    }


def solid_title_style(name, color):
    title_name = str(name or '').strip()
    if not title_name:
        raise ValueError('称号名称不能为空')
    if len(title_name) > TITLE_STYLE_MAX_TEXT:
        raise ValueError(f'称号名称最长{TITLE_STYLE_MAX_TEXT}个字符')
    paint = _solid_paint(color)
    return {
        'version': TITLE_STYLE_VERSION,
        'segments': [_make_segment(0, title_name, paint)],
    }


def parse_title_style(markup, fallback_color='neutral'):
    """Parse safe, non-nesting title markup into a renderer-neutral AST."""
    source = str(markup or '').strip()
    if not source:
        raise ValueError('称号样式不能为空')
    if '{' not in source:
        return solid_title_style(source, fallback_color)

    segments = []
    cursor = 0
    while cursor < len(source):
        if source[cursor] != '{':
            next_open = source.find('{', cursor)
            end = len(source) if next_open < 0 else next_open
            text = source[cursor:end]
            if text:
                segments.append(_make_segment(len(segments), text, _solid_paint(fallback_color)))
            cursor = end
            continue
        tag_end = source.find('}', cursor + 1)
        if tag_end < 0:
            raise ValueError(f'称号样式在第{cursor + 1}个字符处缺少 }}')
        tag = source[cursor + 1:tag_end].strip()
        if tag == '/':
            raise ValueError(f'称号样式在第{cursor + 1}个字符处存在多余的关闭标记')
        close_at = source.find('{/}', tag_end + 1)
        if close_at < 0:
            raise ValueError(f'样式段 {tag} 缺少 {{/}}')
        text = source[tag_end + 1:close_at]
        if '{' in text or '}' in text:
            raise ValueError('称号样式不支持嵌套；请拆分为多个相邻样式段')
        style_tag, marker, explicit_id = tag.rpartition('|id=')
        if not marker:
            style_tag, explicit_id = tag, ''
        paint = _parse_paint_tag(style_tag)
        segments.append(_make_segment(len(segments), text, paint, explicit_id=explicit_id.strip()))
        cursor = close_at + 3

    if not segments:
        raise ValueError('称号样式没有可显示内容')
    if len(segments) > TITLE_STYLE_MAX_SEGMENTS:
        raise ValueError(f'称号最多包含{TITLE_STYLE_MAX_SEGMENTS}个样式段')
    plain = ''.join(item['text'] for item in segments)
    if len(plain) > TITLE_STYLE_MAX_TEXT:
        raise ValueError(f'称号名称最长{TITLE_STYLE_MAX_TEXT}个字符')
    seen = set()
    for segment in segments:
        if segment['id'] in seen:
            raise ValueError(f'样式段 ID 重复：{segment["id"]}')
        seen.add(segment['id'])
    return {'version': TITLE_STYLE_VERSION, 'segments': segments}


def normalize_title_style(value, name='', color='neutral'):
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith('{'):
            try:
                value = json.loads(stripped)
            except (TypeError, ValueError, json.JSONDecodeError):
                value = parse_title_style(stripped, fallback_color=color)
        else:
            value = parse_title_style(stripped, fallback_color=color)
    if not isinstance(value, dict):
        return solid_title_style(name, color)
    segments = value.get('segments')
    if not isinstance(segments, list) or not segments:
        return solid_title_style(name, color)
    normalized = []
    for index, raw in enumerate(segments[:TITLE_STYLE_MAX_SEGMENTS]):
        if not isinstance(raw, dict):
            raise ValueError('称号样式段格式错误')
        text = str(raw.get('text') or '')
        paint = normalize_title_paint(raw.get('paint'))
        normalized.append(_make_segment(index, text, paint, explicit_id=str(raw.get('id') or '')))
    result = {'version': TITLE_STYLE_VERSION, 'segments': normalized}
    if len(title_style_plain_text(result)) > TITLE_STYLE_MAX_TEXT:
        raise ValueError(f'称号名称最长{TITLE_STYLE_MAX_TEXT}个字符')
    return result


def normalize_title_paint(value):
    if not isinstance(value, dict):
        return _solid_paint(value or 'neutral')
    kind = str(value.get('kind') or '').strip().lower()
    if kind == 'solid':
        return _solid_paint(value.get('color'))
    if kind in {'gradient', 'rainbow'}:
        colors = [normalize_title_color(item) for item in list(value.get('colors') or [])]
        if len(colors) < 2 or any(not item for item in colors):
            raise ValueError('渐变颜色无效')
        return {'kind': kind, 'angle': _normalize_angle(value.get('angle')), 'colors': colors[:12]}
    if kind == 'theme':
        return {
            'kind': 'theme',
            'light': normalize_title_paint(value.get('light')),
            'dark': normalize_title_paint(value.get('dark')),
        }
    raise ValueError(f'未知称号绘制类型：{kind}')


def title_style_plain_text(style):
    return ''.join(str(item.get('text') or '') for item in (style or {}).get('segments') or [])


def title_style_json(style):
    return json.dumps(style, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def title_style_fallback_color(style, fallback='neutral'):
    segments = list((style or {}).get('segments') or [])
    if not segments:
        return normalize_title_color(fallback, 'neutral') or 'neutral'
    paint = segments[0].get('paint') or {}
    while paint.get('kind') == 'theme':
        paint = paint.get('light') or paint.get('dark') or {}
    if paint.get('kind') == 'solid':
        return normalize_title_color(paint.get('color'), fallback) or fallback
    colors = paint.get('colors') or []
    return normalize_title_color(colors[0] if colors else fallback, fallback) or fallback


def title_style_segment(style, segment_id):
    key = str(segment_id or '').strip()
    for segment in (style or {}).get('segments') or []:
        if str(segment.get('id') or '') == key:
            return segment
    return None
