# -*- coding: utf-8 -*-
"""把游戏的卡面渲染器整套搬到编辑器里（card-exporter 的做法）。

游戏自己的卡面渲染入口是 ``window.GTN_CARD_RENDERER``（在 ``static/js/game.js`` 里），
提供 ``setCardDefs(defs)`` / ``setOptions(...)`` / ``createCardElement(cardDict)``。
card-exporter 之所以渲染得和游戏一模一样，就是因为它在普通页面里加载了同一份
``game.js``，再用 ``setCardDefs()`` 把卡数据喂进去。

编辑器照抄这条路：把渲染器依赖的资源复制到 ``模组编辑器/src/generated/vendor/``，
预览用 iframe 加载它们，从而一次性消掉所有样式偏差。

    python tools/extract_renderer_vendor.py
"""

from __future__ import annotations

import argparse
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT.parent / "模组编辑器" / "src" / "generated" / "vendor"

# 渲染卡面真正需要的东西：脚本、样式、字体、图标。
COPY_FILES = (
    ("static/js/game.js", "game.js"),
    ("static/css/style.css", "style.css"),
)
COPY_DIRS = (
    ("static/fonts", "fonts"),
    ("static/assets/ui-icons", "assets/ui-icons"),
    ("static/assets/status-icons", "assets/status-icons"),
)

# 字体只要 woff2：.ttf 是同一套字形的全量版（8.5 MB），浏览器按 @font-face 走 woff2。
FONT_SUFFIXES = (".woff2",)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="复制游戏卡面渲染器到编辑器。")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    total = 0
    for source_rel, target_rel in COPY_FILES:
        source = ROOT / source_rel
        if not source.is_file():
            print(f"缺少文件：{source_rel}")
            return 2
        target = out / target_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        total += target.stat().st_size
        print(f"copy {source_rel} -> {target_rel} ({target.stat().st_size // 1024} KB)")

    # 游戏的样式与脚本用站点绝对路径（/fonts/、/static/assets/）。编辑器里这些资源
    # 与 vendor 同级，改成相对路径，host 页面用 <base> 指到 vendor 目录即可解析。
    for name, pairs in (
        ("style.css", (("url('/fonts/", "url('./fonts/"), ("url(\"/fonts/", "url(\"./fonts/"))),
        ("game.js", (("'/static/assets/", "'./assets/"), ("\"/static/assets/", "\"./assets/"),
                     ("`/static/assets/", "`./assets/"))),
    ):
        path = out / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        before = text
        for old, new in pairs:
            text = text.replace(old, new)
        if text != before:
            path.write_text(text, encoding="utf-8")
            print(f"rewrite asset paths in {name}")

    for source_rel, target_rel in COPY_DIRS:
        source = ROOT / source_rel
        if not source.is_dir():
            continue
        target = out / target_rel
        shutil.copytree(source, target, dirs_exist_ok=True)
        if source_rel.endswith("fonts"):
            for extra in target.iterdir():
                if extra.is_file() and extra.suffix.lower() not in FONT_SUFFIXES:
                    extra.unlink()
        size = sum(path.stat().st_size for path in target.rglob("*") if path.is_file())
        total += size
        print(f"copy {source_rel}/ -> {target_rel}/ ({size // 1024} KB)")

    print(f"vendor 总大小：{total // 1024 // 1024} MB")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
