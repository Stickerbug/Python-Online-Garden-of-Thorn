"""
GB2312 level-1 汉字区包含 3755 个简体汉字。
这是 GTN 字体子集化的基础区域。
"""

from functools import lru_cache


@lru_cache(maxsize=1)
def get_common_zh_chars() -> str:
    chars = []
    seen = set()
    # GB2312 level-1: zone 16-55, cell 1-94.
    for high in range(0xB0, 0xD8):
        for low in range(0xA1, 0xFF):
            try:
                ch = bytes((high, low)).decode('gb2312')
            except UnicodeDecodeError:
                continue
            if len(ch) != 1 or ch in seen:
                continue
            seen.add(ch)
            chars.append(ch)
    return ''.join(chars)

