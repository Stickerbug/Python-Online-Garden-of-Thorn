from pathlib import Path
import re
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer

NAME="荆棘花园在线卡牌游戏软件"; VERSION="V0.5.17"
ROOT=Path(__file__).resolve().parents[2]; PROJECT=ROOT/"Python联机版"; OUT=ROOT/"软件著作权申请材料"; SHOTS=PROJECT/"tmp/pdfs/screens"
SOURCE=OUT/"用户操作手册正文.md"; PDF=OUT/f"{NAME}{VERSION}用户操作手册.pdf"; REGULAR="MaterialCN"; BOLD="MaterialCNBold"

def register_fonts():
    regular=next(p for p in [Path(r"C:\Windows\Fonts\msyh.ttc"),Path(r"C:\Windows\Fonts\simsun.ttc"),PROJECT/"static/fonts/Kreadon-Regular.ttf"] if p.exists())
    bold=next(p for p in [Path(r"C:\Windows\Fonts\msyhbd.ttc"),Path(r"C:\Windows\Fonts\simhei.ttf"),PROJECT/"static/fonts/Kreadon-Demi.ttf"] if p.exists())
    pdfmetrics.registerFont(TTFont(REGULAR,str(regular))); pdfmetrics.registerFont(TTFont(BOLD,str(bold)))

def styles():
    s=getSampleStyleSheet()
    return {
      "title":ParagraphStyle("titlecn",parent=s["Title"],fontName=BOLD,fontSize=24,leading=34,alignment=TA_CENTER,textColor=colors.HexColor("#173C2C"),spaceAfter=7*mm),
      "subtitle":ParagraphStyle("subtitlecn",parent=s["Normal"],fontName=REGULAR,fontSize=12.5,leading=20,alignment=TA_CENTER,textColor=colors.HexColor("#4D5B54"),spaceAfter=3*mm),
      "h1":ParagraphStyle("h1cn",parent=s["Heading1"],fontName=BOLD,fontSize=17,leading=24,textColor=colors.HexColor("#173C2C"),spaceAfter=4*mm),
      "h2":ParagraphStyle("h2cn",parent=s["Heading2"],fontName=BOLD,fontSize=12.5,leading=18,textColor=colors.HexColor("#315B47"),spaceBefore=2.5*mm,spaceAfter=1.5*mm),
      "body":ParagraphStyle("bodycn",parent=s["BodyText"],fontName=REGULAR,fontSize=9.5,leading=16,alignment=TA_JUSTIFY,firstLineIndent=19,textColor=colors.HexColor("#222222"),spaceAfter=2*mm,wordWrap="CJK"),
      "bullet":ParagraphStyle("bulletcn",parent=s["BodyText"],fontName=REGULAR,fontSize=9.3,leading=15.5,leftIndent=6*mm,firstLineIndent=-4*mm,textColor=colors.HexColor("#222222"),spaceAfter=1.2*mm,wordWrap="CJK"),
      "caption":ParagraphStyle("captioncn",parent=s["Normal"],fontName=REGULAR,fontSize=8,leading=12,alignment=TA_CENTER,textColor=colors.HexColor("#66716B"),spaceBefore=1.2*mm,spaceAfter=2.5*mm),
    }

def P(text,style): return Paragraph(text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"),style)

def header_footer(c,doc):
    c.saveState(); w,h=A4
    if doc.page>1:
        c.setStrokeColor(colors.HexColor("#9EAAA3")); c.setLineWidth(.4); c.line(18*mm,h-15*mm,w-18*mm,h-15*mm); c.line(18*mm,14*mm,w-18*mm,14*mm)
        c.setFont(REGULAR,7.5); c.setFillColor(colors.HexColor("#54645B")); c.drawString(18*mm,h-11.3*mm,f"{NAME} {VERSION} 用户操作手册"); c.drawCentredString(w/2,9.5*mm,f"第 {doc.page} 页")
    c.restoreState()

def image_block(filename,caption,st):
    path=SHOTS/filename
    if not path.exists(): return [P(f"界面截图：{caption}",st["caption"])]
    img=Image(str(path)); width=72*mm; img.drawWidth=width; img.drawHeight=width*img.imageHeight/img.imageWidth; img.hAlign="CENTER"
    return [KeepTogether([img,P(caption,st["caption"])])]

def build():
    register_fonts(); st=styles(); doc=SimpleDocTemplate(str(PDF),pagesize=A4,leftMargin=19*mm,rightMargin=19*mm,topMargin=20*mm,bottomMargin=19*mm,title=f"{NAME}{VERSION}用户操作手册",author="Garden of Thorn Dev Team")
    lines=SOURCE.read_text(encoding="utf-8-sig").splitlines(); story=[]; paragraph=[]; title_seen=0; break_count=0
    def flush():
        nonlocal paragraph
        text="".join(x.strip() for x in paragraph).strip()
        if text: story.append(P(text,st["body"]))
        paragraph=[]
    for raw in lines:
        line=raw.strip()
        if not line: flush(); continue
        if line=="\\pagebreak":
            flush(); break_count+=1
            if break_count<=2: story.append(PageBreak())
            else: story.append(Spacer(1,3*mm))
            continue
        match=re.fullmatch(r"\[\[image:([^|]+)\|([^]]+)\]\]",line)
        if match: flush(); story.extend(image_block(match.group(1),match.group(2),st)); continue
        if line.startswith("# "):
            flush(); title_seen+=1; story.append(P(line[2:],st["title"] if title_seen==1 else st["h1"]));
            if title_seen==1: story.append(Spacer(1,10*mm))
            continue
        if line.startswith("## "):
            flush(); text=line[3:]
            if title_seen==1 and (text.startswith("V") or "用户操作手册" in text): story.append(P(text,st["subtitle"]))
            else: story.append(P(text,st["h2"]))
            continue
        if line.startswith("- "): flush(); story.append(P("• "+line[2:],st["bullet"])); continue
        if re.match(r"^\d+\.\s",line) and title_seen<=2: flush(); story.append(P(line,st["bullet"])); continue
        if title_seen==1 and ("鉴别材料" in line or "材料生成日期" in line): flush(); story.append(P(line,st["subtitle"])); continue
        paragraph.append(line)
    flush(); doc.build(story,onFirstPage=header_footer,onLaterPages=header_footer); print(PDF)
if __name__=="__main__": build()
