# -*- coding: utf-8 -*-
"""从游戏样式里抽出卡面规则，供模组编辑器的卡面预览使用。

编辑器不应该自己画一张"像游戏"的卡——那必然和游戏越来越不像。这里把游戏
``static/css/style.css`` 里所有跟 ``.card`` 有关的规则（含 ``@media`` 包裹的）
连同 ``:root`` 变量一起抽出来，编辑器直接引用生成的文件，卡面就与游戏一致。

游戏改版后重新跑一次即可：

    python tools/extract_card_css.py
    python tools/extract_card_css.py --out ../模组编辑器/prototype/game-card.css
"""

from __future__ import annotations

import argparse
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "static" / "css" / "style.css"
DEFAULT_OUT = ROOT.parent / "模组编辑器" / "src" / "generated" / "game-card.css"
DEFAULT_FONT_SRC = ROOT / "static" / "fonts"

# 卡面本身 + 效果文字里的关键词 chip / 内联图标 / 内联卡牌 chip。
SELECTOR_NEEDLES = (".card", ".card-token", ".inline-token-icon", ".inline-card-chip", ".choice-card")
# 卡面依赖的全局变量与主题覆盖：字体变量、暗色主题、字体加载后的字体切换。
ALWAYS_KEEP_PRELUDES = (":root", "@font-face", "html.fonts-loaded-main", "[data-theme")

# 游戏从站点根目录取字体（/fonts/...），编辑器里字体放在同级的 fonts/ 目录。
FONT_URL_PREFIX = "url('/fonts/"
FONT_URL_REPLACEMENT = "url('./fonts/"


def iter_rules(text: str):
    """产出 (prelude, body, media)：顶层规则与一层 @media/@supports 内的规则。"""

    index = 0
    length = len(text)
    while index < length:
        brace = text.find("{", index)
        if brace < 0:
            return
        prelude = text[index:brace]
        semi = prelude.rfind(";")
        if semi >= 0:
            prelude = prelude[semi + 1:]
        prelude = prelude.strip()
        depth = 1
        cursor = brace + 1
        while cursor < length and depth:
            char = text[cursor]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            cursor += 1
        body = text[brace + 1:cursor - 1]
        if prelude.startswith(("@media", "@supports")):
            for inner_prelude, inner_body, _ in iter_rules(body):
                yield inner_prelude, inner_body, prelude
        else:
            yield prelude, body, ""
        index = cursor


def extract(css_text: str):
    kept = []
    for prelude, body, media in iter_rules(css_text):
        if prelude.startswith(("@keyframes", "@import", "@charset")):
            continue
        wanted = any(needle in prelude for needle in SELECTOR_NEEDLES) or any(
            marker in prelude for marker in ALWAYS_KEEP_PRELUDES
        )
        if not wanted:
            continue
        body = body.replace(FONT_URL_PREFIX, FONT_URL_REPLACEMENT)
        rule = f"{prelude} {{{body}}}"
        kept.append(f"{media} {{ {rule} }}" if media else rule)
    return kept


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="抽取游戏卡面 CSS 供编辑器预览使用。")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="游戏的 style.css")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="输出的 game-card.css")
    parser.add_argument("--fonts-src", default=str(DEFAULT_FONT_SRC), help="游戏的字体目录")
    args = parser.parse_args(argv)

    source = pathlib.Path(args.source)
    target = pathlib.Path(args.out)
    if not source.is_file():
        print(f"找不到样式文件: {source}")
        return 2

    kept = extract(source.read_text(encoding="utf-8"))
    header = (
        "/* 从 Python联机版/static/css/style.css 自动提取的卡面样式。\n"
        "   由 Python联机版/tools/extract_card_css.py 生成，不要手改；\n"
        "   游戏改版后重新运行该脚本即可同步。 */\n\n"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(header + "\n".join(kept) + "\n", encoding="utf-8")

    # 字体跟 CSS 放同一目录下的 fonts/，这样 @font-face 里的 ./fonts/ 才解析得到。
    fonts_src = pathlib.Path(args.fonts_src)
    copied = 0
    if fonts_src.is_dir():
        font_dir = target.parent / "fonts"
        font_dir.mkdir(parents=True, exist_ok=True)
        for font in sorted(fonts_src.glob("*.woff2")):
            shutil.copy2(font, font_dir / font.name)
            copied += 1
    print(f"rules kept: {len(kept)}")
    print(f"fonts copied: {copied}")
    print(f"written: {target} ({target.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
