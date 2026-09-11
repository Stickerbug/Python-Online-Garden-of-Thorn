# -*- coding: utf-8 -*-
"""把 .gtnmod 包里的卡图统一到同一条"卡面尺寸规范"。

规范（见 docs/卡图尺寸规范.md）：

* 根元素 `viewBox="0 0 283.46 283.46"`，**不要** width/height；
* 图形内容（可见像素的包围盒）最大边 = 画布的 60%，居中。

做法：先用 cairosvg 渲染、量出内容的用户坐标包围盒，再把所有图形子节点
包进一个 `<g transform="translate(...) scale(...)">`，使它正好落在目标位置上。
这样贴边导出的图（如 candle.svg）和非正方形画布都能一次规整。

    python tools/normalize_card_art.py --report            # 只报告，不改文件
    python tools/normalize_card_art.py --all --apply       # 全部包按规范规整
    python tools/normalize_card_art.py --verify            # 只校验是否符合规范
"""

from __future__ import annotations

import argparse
import io
import os
import pathlib
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"
SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

DEFAULT_SIZE = 283.46
DEFAULT_RATIO = 0.60
DEFAULT_BAND = 0.05

"""只有这些目录下的图是"卡面美术"；status-icons/ 之类的小图标有自己的规范，不动。"""
ART_PREFIXES = ("card-art/", "assets/cards/", "assets/card-art/", "cards/")


def is_card_art(member: str) -> bool:
    path = member.replace("\\", "/").lower()
    return path.endswith(".svg") and path.startswith(ART_PREFIXES)

ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)


def parse_length(value) -> float:
    match = re.match(r"\s*([0-9.]+)", str(value or ""))
    return float(match.group(1)) if match else 0.0


def view_box_of(root) -> tuple:
    """返回 (x, y, w, h)；缺失时退回 width/height，再退回 0 0 100 100。"""

    raw = str(root.attrib.get("viewBox", "")).replace(",", " ").split()
    if len(raw) == 4:
        try:
            x, y, w, h = (float(value) for value in raw)
            if w > 0 and h > 0:
                return x, y, w, h
        except ValueError:
            pass
    w = parse_length(root.attrib.get("width")) or 100.0
    h = parse_length(root.attrib.get("height")) or 100.0
    return 0.0, 0.0, w, h


def measure(root, raw: bytes, size: int = 512):
    """渲染一次，返回内容包围盒（用户坐标）与画布尺寸。"""

    import cairosvg  # 只在需要测量时导入
    from PIL import Image

    x, y, w, h = view_box_of(root)
    png = cairosvg.svg2png(bytestring=raw, output_width=size, output_height=size)
    image = Image.open(io.BytesIO(png)).convert("RGBA")
    # 只看 alpha：全透明但 RGB 非零的像素不算内容
    box = image.split()[3].getbbox()
    if not box:
        return None
    scale = size / max(w, h)
    offset_x = (size - w * scale) / 2.0
    offset_y = (size - h * scale) / 2.0
    x0 = (box[0] - offset_x) / scale + x
    y0 = (box[1] - offset_y) / scale + y
    x1 = (box[2] - offset_x) / scale + x
    y1 = (box[3] - offset_y) / scale + y
    return {"bbox": (x0, y0, x1, y1), "view": (x, y, w, h), "coverage": max(x1 - x0, y1 - y0) / max(w, h)}


def normalized_svg(raw: bytes, size: float, ratio: float) -> bytes:
    root = ET.fromstring(raw.decode("utf-8-sig"))
    info = measure(root, raw)
    if info is None:
        raise ValueError("图里没有可见内容")
    x0, y0, x1, y1 = info["bbox"]
    width = max(1e-6, x1 - x0)
    height = max(1e-6, y1 - y0)
    scale = (ratio * size) / max(width, height)
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    offset_x = size / 2.0 - scale * cx
    offset_y = size / 2.0 - scale * cy

    group = ET.Element(f"{{{SVG_NS}}}g",
                       {"transform": "translate(%.6f %.6f) scale(%.6f)" % (offset_x, offset_y, scale)})
    preserved, graphics = [], []
    for child in list(root):
        root.remove(child)
        tag = child.tag
        if tag in (f"{{{SVG_NS}}}defs", f"{{{SVG_NS}}}title", f"{{{SVG_NS}}}desc", f"{{{SVG_NS}}}metadata"):
            preserved.append(child)
        else:
            graphics.append(child)
    for child in preserved:
        root.append(child)
    for child in graphics:
        group.append(child)
    root.append(group)

    style = str(root.attrib.get("style") or "")
    if re.search(r"(^|;)\s*(width|height)\s*:", style):
        root.attrib.pop("style", None)
    root.attrib.pop("width", None)
    root.attrib.pop("height", None)
    root.set("viewBox", "0 0 %s %s" % (fmt(size), fmt(size)))
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def fmt(value: float) -> str:
    text = ("%.6f" % float(value)).rstrip("0").rstrip(".")
    return text or "0"


def is_canonical(root, size: float, band: float) -> bool:
    if root.attrib.get("width") or root.attrib.get("height"):
        return False
    view = str(root.attrib.get("viewBox", "")).replace(",", " ").split()
    if len(view) != 4:
        return False
    try:
        x, y, w, h = (float(value) for value in view)
    except ValueError:
        return False
    return abs(x) < 1e-6 and abs(y) < 1e-6 and abs(w - size) < 0.01 and abs(h - size) < 0.01


def canvas_is_broken(root, tolerance: float = 1e-3) -> bool:
    """画布本身是否"不正确"：不是 1:1 正方形（宽高比失真）。

    只带 width/height、或画布尺寸不同（例如 100×100）但**比例是 1:1** 的图，
    在卡面上用 object-fit: contain 渲染，视觉上不会有问题 —— 这类不动。
    """

    _x, _y, w, h = view_box_of(root)
    if w <= 0 or h <= 0:
        return True
    return abs(w - h) > tolerance * max(w, h)
def process_package(path: pathlib.Path, size: float, ratio: float, band: float,
                    apply: bool, verify: bool, canvas_only: bool = False):
    with zipfile.ZipFile(path, "r") as archive:
        members = {item.filename: archive.read(item.filename) for item in archive.infolist()}
    changed, issues, skipped = [], [], []
    for member, content in list(members.items()):
        if not is_card_art(member):
            continue
        try:
            root = ET.fromstring(content.decode("utf-8-sig"))
        except Exception as exc:  # noqa: BLE001
            issues.append((member, "解析失败: %s" % exc))
            continue
        try:
            info = measure(root, content)
        except Exception as exc:  # noqa: BLE001
            issues.append((member, "测量失败: %s" % exc))
            continue
        coverage = info["coverage"] if info else 0.0
        if canvas_only and not canvas_is_broken(root):
            # 画布是 1:1 的，视觉上没问题：一律不动（哪怕内容占比和标准略有出入）
            skipped.append(member)
            continue
        if canvas_only:
            # 只修画布：可见尺寸按"最小改动"落进标准带，不强行拉到中心值
            target_ratio = min(max(coverage, ratio - band), ratio + band)
        else:
            target_ratio = ratio
        canonical = is_canonical(root, size, band)
        in_band = abs(coverage - target_ratio) <= band
        if canonical and in_band:
            skipped.append(member)
            continue
        reason = []
        if not canonical:
            reason.append("画布非标准")
        if not in_band:
            reason.append("内容占比 %.3f" % coverage)
        if verify:
            issues.append((member, "、".join(reason)))
            continue
        if not apply:
            issues.append((member, "、".join(reason)))
            continue
        try:
            members[member] = normalized_svg(content, size, target_ratio)
            changed.append("%s（%s → 新占比 %.3f）" % (member, "、".join(reason), target_ratio))
        except Exception as exc:  # noqa: BLE001
            issues.append((member, "规整失败: %s" % exc))
    if changed:
        handle, temp_name = tempfile.mkstemp(suffix=".gtnmod", dir=str(path.parent))
        os.close(handle)
        temp_path = pathlib.Path(temp_name)
        try:
            with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                for member, content in members.items():
                    archive.writestr(member, content)
            os.replace(temp_path, path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
    return {"changed": changed, "issues": issues, "skipped": len(skipped)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="统一卡图尺寸（规范见 docs/卡图尺寸规范.md）")
    parser.add_argument("packages", nargs="*", help="mods/ 下的包名；留空配合 --all 表示全部")
    parser.add_argument("--all", action="store_true", help="处理 mods/ 下所有 .gtnmod")
    parser.add_argument("--apply", action="store_true", help="真的写回文件（默认只报告）")
    parser.add_argument("--verify", action="store_true", help="只校验，不改文件")
    parser.add_argument("--canvas-only", action="store_true",
                        help="只修画布不是 1:1 的图；画布正确的图一律不动，可见尺寸按最小改动落进标准带")
    parser.add_argument("--size", type=float, default=DEFAULT_SIZE)
    parser.add_argument("--ratio", type=float, default=DEFAULT_RATIO)
    parser.add_argument("--band", type=float, default=DEFAULT_BAND)
    args = parser.parse_args(argv)

    if args.all or not args.packages:
        targets = sorted(MODS.glob("*.gtnmod"))
    else:
        targets = [MODS / name for name in args.packages]

    total_changed = total_issues = 0
    for path in targets:
        if not path.is_file():
            print("!! 找不到包:", path)
            continue
        result = process_package(path, args.size, args.ratio, args.band, args.apply, args.verify, args.canvas_only)
        if result["changed"]:
            print("[改] %s: %d 张" % (path.name, len(result["changed"])))
            for item in result["changed"]:
                print("     ", item)
        if result["issues"]:
            print("[%s] %s: %d 张" % ("不符" if args.verify or not args.apply else "跳过", path.name, len(result["issues"])))
            for member, reason in result["issues"]:
                print("     ", member, "→", reason)
        if not result["changed"] and not result["issues"]:
            print("[好] %s: %d 张全部符合规范" % (path.name, result["skipped"]))
        total_changed += len(result["changed"])
        total_issues += len(result["issues"])
    print()
    print("合计：%s %d 张，%s %d 张" % ("已规整" if args.apply else "待规整", total_changed,
                                       "不符" if args.verify else "待处理/异常", total_issues))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
