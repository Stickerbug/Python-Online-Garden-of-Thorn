import os
import re
import sys
import zipfile

from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter, Options

from common_zh_chars import get_common_zh_chars


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(PROJECT_DIR, 'static', 'fonts')

TEXT_EXTENSIONS = {
    '.py', '.js', '.css', '.html', '.json', '.toml', '.md', '.txt',
}

ZIP_TEXT_EXTENSIONS = {
    '.json', '.txt', '.md',
}

EXCLUDED_DIRS = {
    '.git', '__pycache__', 'venv', '.venv', 'node_modules', '.pytest_cache',
    'third_party', 'vendor', 'assets',
}

EXCLUDED_FILES = {
    # 词库不是玩家可见常规文案，纳入会显著膨胀中文子集。
    os.path.normcase(os.path.join(PROJECT_DIR, 'static', 'data', 'moderation_rules.json')),
    os.path.normcase(os.path.join(PROJECT_DIR, 'playerid_blacklist.txt')),
}

EXTRA_RANGES = [
    (0x3040, 0x309F, '平假名'),
    (0x30A0, 0x30FF, '片假名'),
    (0xFF65, 0xFF9F, '半角片假名'),
]

CJK_FALLBACK_RANGES = [
    (0x2E80, 0x30FF),  # CJK radicals, punctuation, Hiragana and Katakana
    (0x31F0, 0x31FF),  # Katakana phonetic extensions
    (0x3400, 0x4DBF),  # CJK extension A
    (0x4E00, 0x9FFF),  # CJK unified ideographs
    (0xF900, 0xFAFF),  # CJK compatibility ideographs
    (0xFF00, 0xFFEF),  # Full-width forms and half-width Katakana
]


def should_scan_file(fpath):
    norm = os.path.normcase(os.path.abspath(fpath))
    if norm in EXCLUDED_FILES:
        return False
    ext = os.path.splitext(fpath)[1].lower()
    return ext in TEXT_EXTENSIONS


def decode_unicode_escapes(text):
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


def add_text_chars(chars, content):
    before = len(chars)
    chars.update(content)
    decoded = decode_unicode_escapes(content)
    if decoded != content:
        chars.update(decoded)
    return len(chars) - before


def iter_project_text_files():
    for root, dirs, files in os.walk(PROJECT_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for name in files:
            fpath = os.path.join(root, name)
            if should_scan_file(fpath):
                yield fpath


def read_text_file(fpath):
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()


def collect_chars_from_gtnmod(chars, fpath):
    added_total = 0
    try:
        with zipfile.ZipFile(fpath) as zf:
            for info in zf.infolist():
                ext = os.path.splitext(info.filename)[1].lower()
                if ext not in ZIP_TEXT_EXTENSIONS or info.file_size > 512 * 1024:
                    continue
                try:
                    content = zf.read(info).decode('utf-8')
                except UnicodeDecodeError:
                    content = zf.read(info).decode('utf-8', errors='replace')
                added_total += add_text_chars(chars, content)
    except zipfile.BadZipFile:
        print(f'  [跳过] {os.path.relpath(fpath, PROJECT_DIR)} 不是有效 gtnmod/zip')
    return added_total


def collect_chars_from_files():
    chars = set()
    common_zh = get_common_zh_chars()
    chars.update(common_zh)
    print(f'  [+{len(common_zh)}] GB2312 一级常用汉字固定保留')
    for start, end, name in EXTRA_RANGES:
        for cp in range(start, end + 1):
            chars.add(chr(cp))
    scanned = 0
    for fpath in iter_project_text_files():
        content = read_text_file(fpath)
        added = add_text_chars(chars, content)
        fsize = os.path.getsize(fpath)
        rel = os.path.relpath(fpath, PROJECT_DIR)
        print(f'  [{added:+d}] {rel} ({fsize/1024:.0f}KB)')
        scanned += 1
    for root, dirs, files in os.walk(PROJECT_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for name in files:
            if not name.lower().endswith('.gtnmod'):
                continue
            fpath = os.path.join(root, name)
            added = collect_chars_from_gtnmod(chars, fpath)
            rel = os.path.relpath(fpath, PROJECT_DIR)
            print(f'  [{added:+d}] {rel} 包内文本')
            scanned += 1
    print(f'  扫描文件/包: {scanned}')
    return chars


def extract_string_literals(python_content):
    strings = []
    for m in re.finditer(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', python_content):
        strings.append(m.group())
    return strings


def font_unicodes(input_path):
    font = TTFont(input_path, lazy=True)
    try:
        return set(font.getBestCmap() or {})
    finally:
        font.close()


def is_cjk_fallback_char(ch):
    cp = ord(ch)
    return any(start <= cp <= end for start, end in CJK_FALLBACK_RANGES)


def subset_font(input_path, output_path, chars, flavor='woff2'):
    print(f'  加载字体: {input_path}')
    font = TTFont(input_path)

    options = Options()
    options.flavor = flavor
    options.layout_features = ['*']
    options.name_IDs = ['*']
    options.legacy_cmap = True
    options.symbol_cmap = True
    options.drop_tables = ['DSIG', 'MVAR', 'cvar', 'fpgm', 'prep']
    options.hinting = True
    options.desubroutinize = True

    subsetter = Subsetter(options=options)

    requested_unicodes = set()
    for ch in chars:
        cp = ord(ch)
        if cp == 0:
            continue
        requested_unicodes.add(cp)

    supported_unicodes = set(font.getBestCmap() or {})
    unicodes = requested_unicodes & supported_unicodes

    if 0x0000 in supported_unicodes:
        unicodes.add(0x0000)

    subsetter.populate(unicodes=unicodes)

    missing_count = len(requested_unicodes - supported_unicodes)
    print(
        f'  子集化: 请求 {len(requested_unicodes)}，'
        f'源字体支持 {len(unicodes)}，缺失 {missing_count} 个字符'
    )
    subsetter.subset(font)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    font.save(output_path)
    font.close()

    orig_size = os.path.getsize(input_path)
    new_size = os.path.getsize(output_path)
    ratio = new_size / orig_size * 100 if orig_size > 0 else 0
    print(f'  输出: {output_path}')
    print(f'  大小: {orig_size/1024:.1f}KB -> {new_size/1024:.1f}KB ({ratio:.1f}%)')


def main():
    print('=== 字体子集化工具 ===')
    print()

    print('[1] 收集字符集...')
    chars = collect_chars_from_files()

    ascii_printable = set(chr(i) for i in range(0x20, 0x7F))
    chars.update(ascii_printable)

    general_punct = set(chr(i) for i in range(0x2000, 0x2070))
    chars.update(general_punct)

    chars.discard('\r')
    chars.discard('\n')
    chars.discard('\t')

    print(f'  共收集 {len(chars)} 个唯一字符')

    cjk_count = sum(1 for c in chars if 0x4E00 <= ord(c) <= 0x9FFF)
    cjk_ext_a = sum(1 for c in chars if 0x3400 <= ord(c) <= 0x4DBF)
    hiragana = sum(1 for c in chars if 0x3040 <= ord(c) <= 0x309F)
    katakana = sum(1 for c in chars if 0x30A0 <= ord(c) <= 0x30FF)
    katakana_ext = sum(1 for c in chars if 0x31F0 <= ord(c) <= 0x31FF)
    hw_katakana = sum(1 for c in chars if 0xFF65 <= ord(c) <= 0xFF9F)
    hangul = sum(1 for c in chars if 0xAC00 <= ord(c) <= 0xD7AF)
    hangul_jamo = sum(1 for c in chars if 0x1100 <= ord(c) <= 0x11FF)
    latin_count = sum(1 for c in chars if (0x0041 <= ord(c) <= 0x024F) or (0x0300 <= ord(c) <= 0x036F))
    cyrillic_count = sum(1 for c in chars if 0x0400 <= ord(c) <= 0x04FF)
    fullwidth = sum(1 for c in chars if 0xFF00 <= ord(c) <= 0xFFEF)
    print(f'  CJK统一汉字: {cjk_count}, CJK扩展A: {cjk_ext_a}')
    print(f'  平假名: {hiragana}, 片假名: {katakana}, 片假名语音扩展: {katakana_ext}, 半角片假名: {hw_katakana}')
    print(f'  韩文音节: {hangul}, 韩文字母: {hangul_jamo}')
    print(f'  Latin: {latin_count}, Cyrillic: {cyrillic_count}, 全角: {fullwidth}')

    print()
    print('[2] 子集化字体...')

    regular_in = os.path.join(FONTS_DIR, 'Kreadon-Regular.ttf')
    demi_in = os.path.join(FONTS_DIR, 'Kreadon-Demi.ttf')

    regular_out = os.path.join(FONTS_DIR, 'Kreadon-Regular.subset.woff2')
    demi_out = os.path.join(FONTS_DIR, 'Kreadon-Demi.subset.woff2')

    if os.path.exists(regular_in):
        subset_font(regular_in, regular_out, chars, flavor='woff2')
    else:
        print(f'  [跳过] {regular_in} 不存在')

    print()

    if os.path.exists(demi_in):
        subset_font(demi_in, demi_out, chars, flavor='woff2')
    else:
        print(f'  [跳过] {demi_in} 不存在')

    print()

    if os.path.exists(regular_in) and os.path.exists(demi_in):
        regular_supported = font_unicodes(regular_in)
        demi_supported = font_unicodes(demi_in)
        demi_cjk_chars = {
            ch for ch in chars
            if is_cjk_fallback_char(ch)
            and ord(ch) in regular_supported
            and ord(ch) not in demi_supported
        }
        print(
            '  Demi 缺失、可由 Regular 子集补充的中日韩字形: '
            f'{len(demi_cjk_chars)} 个字符'
        )
    else:
        print('  [跳过] 无法检查 Demi 中日韩缺失字形')

    print()
    print('[3] 完成!')


if __name__ == '__main__':
    main()
