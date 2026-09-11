# -*- coding: utf-8 -*-
"""Normalize card-art SVGs inside a .gtnmod package to a 100x100 viewBox.

Cards that moved between official packages must follow the destination
package's art convention, so this reuses the same scaling rules as
tools/build_void_dlc_cards.py.

.. deprecated::
    100×100 / 内容占 82% 这套目标已不符合现行规范（画布 283.46、内容占 60%，
    见 docs/卡图尺寸规范.md）。请改用 ``tools/normalize_card_art.py``。
    本脚本仅作历史参考，不要再对包执行。
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SVG_NS = "{http://www.w3.org/2000/svg}"


def parse_length(value) -> float:
    match = re.match(r"\s*([0-9.]+)", str(value or ""))
    return float(match.group(1)) if match else 100.0


def normalized_svg(raw: bytes) -> bytes:
    root = ET.fromstring(raw.decode("utf-8-sig"))
    view_box = root.attrib.get("viewBox", "").replace(",", " ").split()
    if len(view_box) == 4:
        x, y, width, height = [float(value) for value in view_box]
    else:
        x = y = 0.0
        width = parse_length(root.attrib.get("width"))
        height = parse_length(root.attrib.get("height"))
    width = max(0.001, width)
    height = max(0.001, height)
    scale = min(82.0 / width, 82.0 / height)
    offset_x = (100.0 - width * scale) / 2.0 - x * scale
    offset_y = (100.0 - height * scale) / 2.0 - y * scale
    group = ET.Element(
        f"{SVG_NS}g",
        {"transform": "translate(%.6f %.6f) scale(%.6f)" % (offset_x, offset_y, scale)},
    )
    preserved, graphics = [], []
    for child in list(root):
        root.remove(child)
        if child.tag in (f"{SVG_NS}defs", f"{SVG_NS}title", f"{SVG_NS}desc"):
            preserved.append(child)
        else:
            graphics.append(child)
    for child in preserved:
        root.append(child)
    for child in graphics:
        group.append(child)
    root.append(group)
    root.attrib.pop("style", None)
    root.set("width", "100")
    root.set("height", "100")
    root.set("viewBox", "0 0 100 100")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packages", nargs="+", help="package filenames inside mods/")
    args = parser.parse_args()
    for name in args.packages:
        path = ROOT / "mods" / name
        with zipfile.ZipFile(path, "r") as zf:
            members = {item.filename: zf.read(item.filename) for item in zf.infolist()}
        changed = []
        for member, content in list(members.items()):
            if not member.lower().endswith(".svg"):
                continue
            if b'viewBox="0 0 100 100"' in content:
                continue
            members[member] = normalized_svg(content)
            changed.append(member)
        if not changed:
            print("unchanged", name)
            continue
        handle, temp_name = tempfile.mkstemp(suffix=".gtnmod", dir=str(path.parent))
        os.close(handle)
        temp_path = pathlib.Path(temp_name)
        try:
            with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                for member, content in members.items():
                    zf.writestr(member, content)
            os.replace(temp_path, path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
        print("normalized", name, "->", len(changed), "svgs:", ", ".join(changed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
