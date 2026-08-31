from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


NAME = "荆棘花园在线卡牌游戏软件"
VERSION = "V0.5.17"
ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "Python联机版"
OUT = ROOT / "软件著作权申请材料"
SHOTS = PROJECT / "output" / "playwright" / "copyright"
OLD_SHOTS = PROJECT / "tmp" / "pdfs" / "screens"
ENEMY_CACHE = PROJECT / "tmp" / "pdfs" / "enemy_png"
SOURCE = OUT / "用户操作手册正文.md"
PDF = OUT / f"{NAME}{VERSION}用户操作手册.pdf"
REGULAR = "MaterialCN"
BOLD = "MaterialCNBold"


def register_fonts() -> None:
    regular = next(
        p
        for p in (
            Path(r"C:\Windows\Fonts\msyh.ttc"),
            Path(r"C:\Windows\Fonts\simsun.ttc"),
            PROJECT / "static" / "fonts" / "Kreadon-Regular.ttf",
        )
        if p.exists()
    )
    bold = next(
        p
        for p in (
            Path(r"C:\Windows\Fonts\msyhbd.ttc"),
            Path(r"C:\Windows\Fonts\simhei.ttf"),
            PROJECT / "static" / "fonts" / "Kreadon-Demi.ttf",
        )
        if p.exists()
    )
    pdfmetrics.registerFont(TTFont(REGULAR, str(regular)))
    pdfmetrics.registerFont(TTFont(BOLD, str(bold)))


def styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "titlecn", parent=sample["Title"], fontName=BOLD, fontSize=24, leading=34,
            alignment=TA_CENTER, textColor=colors.HexColor("#173C2C"), spaceAfter=7 * mm,
        ),
        "subtitle": ParagraphStyle(
            "subtitlecn", parent=sample["Normal"], fontName=REGULAR, fontSize=12.5,
            leading=20, alignment=TA_CENTER, textColor=colors.HexColor("#4D5B54"), spaceAfter=3 * mm,
        ),
        "h1": ParagraphStyle(
            "h1cn", parent=sample["Heading1"], fontName=BOLD, fontSize=17, leading=24,
            textColor=colors.HexColor("#173C2C"), spaceAfter=4 * mm, keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "h2cn", parent=sample["Heading2"], fontName=BOLD, fontSize=12.5, leading=18,
            textColor=colors.HexColor("#315B47"), spaceBefore=2.5 * mm, spaceAfter=1.5 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "bodycn", parent=sample["BodyText"], fontName=REGULAR, fontSize=9.5, leading=16,
            alignment=TA_JUSTIFY, firstLineIndent=19, textColor=colors.HexColor("#222222"),
            spaceAfter=2 * mm, wordWrap="CJK",
        ),
        "bullet": ParagraphStyle(
            "bulletcn", parent=sample["BodyText"], fontName=REGULAR, fontSize=9.2, leading=15,
            leftIndent=6 * mm, firstLineIndent=-4 * mm, textColor=colors.HexColor("#222222"),
            spaceAfter=1.1 * mm, wordWrap="CJK",
        ),
        "callout": ParagraphStyle(
            "calloutcn", parent=sample["BodyText"], fontName=REGULAR, fontSize=9.2, leading=15,
            leftIndent=4 * mm, rightIndent=4 * mm, textColor=colors.HexColor("#234735"),
            backColor=colors.HexColor("#EEF6F1"), borderColor=colors.HexColor("#8CB49E"),
            borderWidth=0.5, borderPadding=7, spaceBefore=1 * mm, spaceAfter=3 * mm, wordWrap="CJK",
        ),
        "caption": ParagraphStyle(
            "captioncn", parent=sample["Normal"], fontName=REGULAR, fontSize=8.2, leading=12,
            alignment=TA_CENTER, textColor=colors.HexColor("#66716B"), spaceBefore=1.2 * mm,
            spaceAfter=2.5 * mm, wordWrap="CJK",
        ),
        "gallery": ParagraphStyle(
            "gallerycn", parent=sample["Normal"], fontName=REGULAR, fontSize=7.2, leading=10,
            alignment=TA_CENTER, textColor=colors.HexColor("#26362E"), wordWrap="CJK",
        ),
        "warning_title": ParagraphStyle(
            "warningtitle", parent=sample["Heading1"], fontName=BOLD, fontSize=21, leading=29,
            alignment=TA_CENTER, textColor=colors.HexColor("#8F251B"), spaceAfter=4 * mm,
        ),
        "warning_line": ParagraphStyle(
            "warningline", parent=sample["BodyText"], fontName=BOLD, fontSize=13, leading=24,
            alignment=TA_CENTER, textColor=colors.HexColor("#4D201B"), wordWrap="CJK",
        ),
    }


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(esc(text), style)


def header_footer(pdf_canvas, doc) -> None:
    pdf_canvas.saveState()
    width, height = A4
    if doc.page > 1:
        pdf_canvas.setStrokeColor(colors.HexColor("#9EAAA3"))
        pdf_canvas.setLineWidth(0.4)
        pdf_canvas.line(18 * mm, height - 15 * mm, width - 18 * mm, height - 15 * mm)
        pdf_canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
        pdf_canvas.setFont(REGULAR, 7.5)
        pdf_canvas.setFillColor(colors.HexColor("#54645B"))
        pdf_canvas.drawString(18 * mm, height - 11.3 * mm, f"{NAME} {VERSION} 用户操作手册")
        pdf_canvas.drawRightString(width - 18 * mm, height - 11.3 * mm, "软件著作权登记补正鉴别材料")
        pdf_canvas.drawCentredString(width / 2, 9.5 * mm, f"第 {doc.page - 1} 页")
    pdf_canvas.restoreState()


def find_image(filename: str) -> Path | None:
    for base in (SHOTS, OLD_SHOTS):
        path = base / filename
        if path.exists():
            return path
    return None


def image_block(filename: str, caption: str, st: dict[str, ParagraphStyle]) -> list:
    path = find_image(filename)
    if not path:
        return [paragraph(f"截图待补：{caption}", st["callout"])]
    image = Image(str(path))
    max_width = 170 * mm
    max_height = 116 * mm
    ratio = min(max_width / image.imageWidth, max_height / image.imageHeight)
    image.drawWidth = image.imageWidth * ratio
    image.drawHeight = image.imageHeight * ratio
    image.hAlign = "CENTER"
    return [KeepTogether([image, paragraph(caption, st["caption"])])]


def health_warning(st: dict[str, ParagraphStyle]) -> list:
    lines = [
        "抵制不良游戏，拒绝盗版游戏。",
        "注意自我保护，谨防受骗上当。",
        "适度游戏益脑，沉迷游戏伤身。",
        "合理安排时间，享受健康生活。",
    ]
    warning = Table([[paragraph(line, st["warning_line"])] for line in lines], colWidths=[164 * mm], hAlign="CENTER")
    warning.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF4EA")),
        ("BOX", (0, 0), (-1, -1), 1.1, colors.HexColor("#C65A3D")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#EDC9B8")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return [
        paragraph("健康游戏忠告与适龄提示", st["warning_title"]),
        Spacer(1, 4 * mm), warning, Spacer(1, 8 * mm),
        paragraph(
            "适龄提示：建议12周岁以上用户使用。游戏包含策略卡牌、在线对战、随机抽牌、文字聊天及故事战斗内容；未成年人应在监护人指导下使用。该提示为开发者依据游戏内容作出的使用建议，不替代主管部门审批或分级结论。",
            st["callout"],
        ),
        paragraph(
            "正式面向公众提供网络游戏服务时，应依法落实真实身份信息验证、防沉迷、未成年人使用时段与时长管理、付费管理、适龄提示和监护人保护机制。截图中的游客或本地测试入口只用于说明软件功能，不表示正式运营环境可以向未实名用户开放游戏服务。",
            st["callout"],
        ),
    ]


def _magick_binary() -> str | None:
    candidates = [shutil.which("magick"), r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"]
    return next((item for item in candidates if item and Path(item).exists()), None)


def _enemy_png(svg_path: Path) -> Path | None:
    ENEMY_CACHE.mkdir(parents=True, exist_ok=True)
    target = ENEMY_CACHE / f"{svg_path.stem}.png"
    if target.exists() and target.stat().st_mtime >= svg_path.stat().st_mtime:
        return target
    magick = _magick_binary()
    if not magick:
        return None
    subprocess.run(
        [magick, "-background", "none", str(svg_path), "-resize", "360x300", str(target)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return target


def enemy_gallery(st: dict[str, ParagraphStyle]) -> list:
    sys.path.insert(0, str(PROJECT))
    from story_content import STORY_ENEMIES  # pylint: disable=import-outside-toplevel

    boundaries = [
        ("花园区域角色与首领", "soldier_ant", "cicada"),
        ("沙漠区域角色与首领", "sandstorm", "desert_centipede"),
        ("海洋区域角色与首领", "ocean_bubble", "wreckage"),
        ("丛林区域角色与首领", "termite_soldier", "magic_firefly"),
        ("工厂区域角色与首领", "mechanical_flower", "generator"),
    ]
    entries = list(STORY_ENEMIES.items())
    positions = {enemy_id: index for index, (enemy_id, _) in enumerate(entries)}
    result: list = []
    for group_index, (title, first_id, last_id) in enumerate(boundaries):
        if group_index:
            result.append(PageBreak())
        result.append(paragraph(title, st["h1"]))
        result.append(paragraph(
            "下列图像为该区域在故事战斗、精英战、事件战或首领战中可能出现的全部固定生物形象；同一角色在不同难度下可能拥有不同数值或行动。",
            st["body"],
        ))
        subset = entries[positions[first_id] : positions[last_id] + 1]
        cells = []
        for enemy_id, enemy in subset:
            image_url = str(enemy.get("image_url") or "")
            svg_path = PROJECT.joinpath(*image_url.lstrip("/").split("/"))
            png_path = _enemy_png(svg_path) if svg_path.exists() else None
            cell_flowables = []
            if png_path:
                image = Image(str(png_path), width=27 * mm, height=22.5 * mm)
                image.hAlign = "CENTER"
                cell_flowables.append(image)
            zh_name = str((enemy.get("name") or {}).get("zh") or enemy_id)
            en_name = str((enemy.get("name") or {}).get("en") or "")
            cell_flowables.append(Paragraph(f"{esc(zh_name)}<br/>{esc(en_name)}<br/>{esc(enemy_id)}", st["gallery"]))
            cells.append(cell_flowables)
        while len(cells) % 4:
            cells.append([])
        rows = [cells[index : index + 4] for index in range(0, len(cells), 4)]
        gallery = Table(rows, colWidths=[42.5 * mm] * 4, rowHeights=[39 * mm] * len(rows), hAlign="CENTER")
        gallery.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#9BB2A5")),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD8D0")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAF8")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        result.append(gallery)
    return result


def build() -> None:
    register_fonts()
    st = styles()
    doc = SimpleDocTemplate(
        str(PDF), pagesize=A4, leftMargin=19 * mm, rightMargin=19 * mm,
        topMargin=20 * mm, bottomMargin=19 * mm,
        title=f"{NAME}{VERSION}用户操作手册", author="Garden of Thorn Dev Team",
        subject="计算机软件著作权登记补正鉴别材料",
    )
    lines = SOURCE.read_text(encoding="utf-8-sig").splitlines()
    story: list = []
    buffered: list[str] = []
    title_seen = 0

    def flush() -> None:
        nonlocal buffered
        text = "".join(item.strip() for item in buffered).strip()
        if text:
            story.append(paragraph(text, st["body"]))
        buffered = []

    for raw in lines:
        line = raw.strip()
        if not line:
            flush()
            continue
        if line == "\\pagebreak":
            flush(); story.append(PageBreak()); continue
        if line == "[[health-warning]]":
            flush(); story.extend(health_warning(st)); continue
        if line == "[[enemy-gallery]]":
            flush(); story.extend(enemy_gallery(st)); continue
        match = re.fullmatch(r"\[\[image:([^|]+)\|([^]]+)\]\]", line)
        if match:
            flush(); story.extend(image_block(match.group(1), match.group(2), st)); continue
        if line.startswith("# "):
            flush(); title_seen += 1
            story.append(paragraph(line[2:], st["title"] if title_seen == 1 else st["h1"]))
            if title_seen == 1:
                story.append(Spacer(1, 10 * mm))
            continue
        if line.startswith("## "):
            flush(); text = line[3:]
            if title_seen == 1 and (text.startswith("V") or "用户操作手册" in text):
                story.append(paragraph(text, st["subtitle"]))
            else:
                story.append(paragraph(text, st["h2"]))
            continue
        if line.startswith("> "):
            flush(); story.append(paragraph(line[2:], st["callout"])); continue
        if line.startswith("- "):
            flush(); story.append(paragraph("• " + line[2:], st["bullet"])); continue
        if re.match(r"^\d+\.\s", line):
            flush(); story.append(paragraph(line, st["bullet"])); continue
        if title_seen == 1 and ("鉴别材料" in line or "材料生成日期" in line):
            flush(); story.append(paragraph(line, st["subtitle"])); continue
        buffered.append(line)
    flush()
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(PDF)


if __name__ == "__main__":
    build()
