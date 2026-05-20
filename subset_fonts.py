import os
import re
import sys

from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter, Options


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(PROJECT_DIR, 'static', 'fonts')

SOURCE_FILES = [
    os.path.join(PROJECT_DIR, 'cards.py'),
    os.path.join(PROJECT_DIR, 'game_engine.py'),
    os.path.join(PROJECT_DIR, 'static', 'js', 'game.js'),
    os.path.join(PROJECT_DIR, 'templates', 'index.html'),
    os.path.join(PROJECT_DIR, 'mod_loader.py'),
    os.path.join(PROJECT_DIR, 'app.py'),
]

EXTRA_RANGES = [
    (0x3040, 0x309F, '平假名'),
    (0x30A0, 0x30FF, '片假名'),
    (0xFF65, 0xFF9F, '半角片假名'),
    (0xAC00, 0xD7AF, '韩文音节'),
    (0x1100, 0x11FF, '韩文字母'),
]


def collect_chars_from_files():
    chars = set()
    for start, end, name in EXTRA_RANGES:
        for cp in range(start, end + 1):
            chars.add(chr(cp))
    for fpath in SOURCE_FILES:
        if not os.path.exists(fpath):
            print(f'  [跳过] {fpath} 不存在')
            continue
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        before = len(chars)
        for ch in content:
            chars.add(ch)
        added = len(chars) - before
        fsize = os.path.getsize(fpath)
        ja_chars_in_file = sum(1 for c in content if 0x3040 <= ord(c) <= 0x309F or 0x30A0 <= ord(c) <= 0x30FF)
        print(f'  [{added:+d}] {os.path.basename(fpath)} ({fsize/1024:.0f}KB, 日文字符: {ja_chars_in_file})')
    return chars


def extract_string_literals(python_content):
    strings = []
    for m in re.finditer(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', python_content):
        strings.append(m.group())
    return strings


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

    unicodes = set()
    for ch in chars:
        cp = ord(ch)
        if cp == 0:
            continue
        unicodes.add(cp)

    unicodes.add(0x0000)

    subsetter.populate(unicodes=unicodes)

    print(f'  子集化: {len(unicodes)} 个字符')
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
    print('[3] 完成!')


if __name__ == '__main__':
    main()
