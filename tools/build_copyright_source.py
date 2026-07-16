from pathlib import Path
from dataclasses import dataclass
import hashlib
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

NAME="荆棘花园在线卡牌游戏软件"; VERSION="V0.5.17"
ROOT=Path(__file__).resolve().parents[2]; PROJECT=ROOT/"Python联机版"; OUT=ROOT/"软件著作权申请材料"
PDF=OUT/f"{NAME}{VERSION}源程序.pdf"; MANIFEST=OUT/"源程序文件清单.txt"; REGULAR="MaterialCN"

def register_font():
    choices=[Path(r"C:\Windows\Fonts\msyh.ttc"),Path(r"C:\Windows\Fonts\simsun.ttc"),PROJECT/"static/fonts/Kreadon-Regular.ttf"]
    pdfmetrics.registerFont(TTFont(REGULAR,str(next(p for p in choices if p.exists()))))

def files():
    preferred=["cards.py","damage_types.py","game_engine.py","game_engine_2v2.py","game_engine_urf.py","mod_spec_v2.py","mod_validator_v2.py","mod_loader.py","mod_loadout_v2.py","mod_runtime_v2.py","replay_core.py","db.py","app.py","card_i18n.py","mod_i18n.py","moderation.py","security.py","r2_mods.py","runtime_errors.py","common_zh_chars.py","font_subsets.py","subset_fonts.py"]
    result=[]; seen=set()
    def add(p):
        if p.is_file() and p.resolve() not in seen: result.append(p); seen.add(p.resolve())
    for name in preferred: add(PROJECT/name)
    for pattern in ["templates/*.html","static/css/*.css"]:
        for p in sorted(PROJECT.glob(pattern),key=lambda x:x.as_posix().lower()):
            if ".min." not in p.name: add(p)
    js=sorted(PROJECT.glob("static/js/*.js"),key=lambda p:(p.name=="game.js",p.name.lower()))
    for p in js:
        if ".min." not in p.name and not p.name.endswith(".map"): add(p)
    return result

@dataclass
class Line:
    number:int; file:str; file_line:int; text:str

def load():
    stream=[]; manifest=[]; number=0
    for p in files():
        rel=p.relative_to(PROJECT).as_posix(); raw=p.read_text(encoding="utf-8-sig",errors="replace"); start=number+1; count=0
        for file_line,text in enumerate(raw.splitlines(),1):
            text=text.expandtabs(4).rstrip()
            if not text.strip(): continue
            number+=1; count+=1; stream.append(Line(number,rel,file_line,text))
        manifest.append((rel,start if count else 0,number if count else 0,count,len(raw.splitlines()),hashlib.sha256(p.read_bytes()).hexdigest()))
    return stream,manifest

def wrap(stream,width=150):
    out=[]
    for item in stream:
        text=item.text
        if len(text)<=width: out.append((item,text,False)); continue
        indent=" "*min(len(text)-len(text.lstrip())+4,28); first=True
        while text:
            room=width if first else width-len(indent); cut=min(room,len(text))
            if len(text)>room:
                space=text.rfind(" ",0,room+1)
                if space>=room//2: cut=space
            part,text=text[:cut],text[cut:].lstrip(); out.append((item,part if first else indent+part,not first)); first=False
    return out

def build_pdf(stream):
    display=wrap(stream)
    if len(display)<3000: raise RuntimeError("源程序不足60页，应提交全部源程序")
    selected=display[:1500]+display[-1500:]; w,h=A4; left,right=14*mm,w-14*mm; top,bottom=h-19*mm,13*mm; leading=(top-bottom)/50
    c=canvas.Canvas(str(PDF),pagesize=A4,pageCompression=1); c.setTitle(f"{NAME}{VERSION}源程序")
    for page in range(60):
        rows=selected[page*50:(page+1)*50]; c.setStrokeColor(colors.HexColor("#666666")); c.setLineWidth(.35); c.line(left,h-14.2*mm,right,h-14.2*mm)
        c.setFillColor(colors.HexColor("#222222")); c.setFont(REGULAR,8); c.drawString(left,h-10.5*mm,f"{NAME} {VERSION}  源程序{'前段' if page<30 else '后段'}")
        a,b=rows[0][0].file,rows[-1][0].file; c.setFont(REGULAR,6.5); c.drawRightString(right,h-10.5*mm,a if a==b else f"{a} 至 {b}")
        y=top-leading+2.2
        for item,text,cont in rows:
            rendered=("       " if cont else f"{item.number:06d} ")+text; c.setFont("Courier",6.35); c.setFillColor(colors.black)
            natural=pdfmetrics.stringWidth(rendered,"Courier",6.35); scale=min(1,(right-left)/natural) if natural else 1
            c.saveState(); c.translate(left,y); c.scale(scale,1); c.drawString(0,0,rendered); c.restoreState(); y-=leading
        c.setStrokeColor(colors.HexColor("#999999")); c.line(left,10.3*mm,right,10.3*mm); c.setFont(REGULAR,7); c.setFillColor(colors.HexColor("#444444")); c.drawCentredString(w/2,6.7*mm,f"第 {page+1} 页，共 60 页"); c.showPage()
    c.save()

def write_manifest(stream,rows):
    text=[f"软件名称：{NAME}",f"版本号：{VERSION}",f"工程目录：{PROJECT}",f"纳入的非空源程序行数：{len(stream)}","","序号\t全局非空行范围\t非空行\t物理行\tSHA-256\t文件"]
    for i,(path,start,end,count,physical,digest) in enumerate(rows,1): text.append(f"{i}\t{start}-{end}\t{count}\t{physical}\t{digest}\t{path}")
    MANIFEST.write_text("\n".join(text)+"\n",encoding="utf-8-sig")

def main():
    OUT.mkdir(parents=True,exist_ok=True); register_font(); stream,manifest=load(); build_pdf(stream); write_manifest(stream,manifest); print(PDF); print(f"files={len(manifest)} nonempty={len(stream)}")
if __name__=="__main__": main()