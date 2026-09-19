# -*- coding: utf-8 -*-
"""把 ``official_statuses.py`` 的官方状态内置表同步进 ``static/js/game.js``。

Round 107 / 批次 DE（方案 B）：状态声明不再放在官方包里，客户端要有一份
与引擎同源的 ``CORE_STATUS_DEFS``。手抄 17 条 × 4 语言必然对不上，所以这里
用生成的方式维护：``game.js`` 里那段带标记的块由本脚本重写。

用法::

    python tools/sync_core_status_defs.py            # 重写 game.js 里的块
    python tools/sync_core_status_defs.py --check     # 只对拍（对不上非零退出）
"""

from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import official_statuses  # noqa: E402

GAME_JS = ROOT / "static" / "js" / "game.js"
BEGIN_MARKER = "// ==== CORE_STATUS_DEFS BEGIN（由 tools/sync_core_status_defs.py 生成，勿手改）===="
END_MARKER = "// ==== CORE_STATUS_DEFS END ===="


def js_string(value: str) -> str:
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def render_block() -> str:
    lines = [BEGIN_MARKER, "const CORE_STATUS_DEFS = ["]
    for entry in official_statuses.client_defs():
        names = ", ".join(f"{lang}: {js_string(text)}"
                          for lang, text in entry["name_i18n"].items())
        descs = ", ".join(f"{lang}: {js_string(text)}"
                          for lang, text in entry["description_i18n"].items())
        visible = "true" if entry["visible"] else "false"
        lines.append("    {")
        lines.append(f"        id: {js_string(entry['id'])}, alias: {js_string(entry['alias'])},")
        lines.append(f"        name_i18n: {{ {names} }},")
        lines.append(f"        description_i18n: {{ {descs} }},")
        lines.append(f"        color: {js_string(entry['color'])}, icon: {js_string(entry['icon'])}, "
                     f"stacking: {js_string(entry['stacking'])}, visible: {visible},")
        lines.append("    },")
    lines.append("];")
    lines.append(END_MARKER)
    return "\n".join(lines)


def locate(text: str) -> tuple:
    start = text.find(BEGIN_MARKER)
    end = text.find(END_MARKER)
    if start < 0 or end < 0 or end < start:
        raise SystemExit(f"game.js 里找不到内置状态表标记（{BEGIN_MARKER} … {END_MARKER}）")
    return start, end + len(END_MARKER)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只对拍，不写文件")
    args = parser.parse_args()

    text = GAME_JS.read_text(encoding="utf-8")
    start, end = locate(text)
    expected = render_block()
    current = text[start:end]
    if current == expected:
        print("CORE_STATUS_DEFS 已同步：%d 条" % len(official_statuses.client_defs()))
        return 0
    if args.check:
        print("CORE_STATUS_DEFS 与 official_statuses.py 不一致，请运行 "
              "`python tools/sync_core_status_defs.py`", file=sys.stderr)
        return 1
    GAME_JS.write_text(text[:start] + expected + text[end:], encoding="utf-8", newline="")
    print("CORE_STATUS_DEFS 已重写：%d 条" % len(official_statuses.client_defs()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
