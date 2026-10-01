# -*- coding: utf-8 -*-
"""图鉴冒烟：temp 系隐藏、不灭合一、颜色、使用卡并集。"""
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(r'C:\Users\bug\AppData\Local\Temp\gallery_smoke')
OUT.mkdir(exist_ok=True)
game_js = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')

# defs：Coral 带 preserve_fission(旧名)、Dianthus 带 amplify(旧名)、Basic 带 temp_swift
defs = {
    'Coral': dict(id='Coral', def_id='Coral', name='珊瑚', name_cn='珊瑚', name_en='Coral',
                  card_type='thorn', cost_e=1, cost_m=0, flags=['preserve_fission'],
                  fission_level=4, fusion_level=1, hits=1, copy_count=0, charge_value=0,
                  swift_value=0, magic_swift_value=0, effect_text='', description=''),
    'Dianthus': dict(id='Dianthus', def_id='Dianthus', name='绿石竹', name_cn='绿石竹', name_en='Dianthus',
                     card_type='thorn', cost_e=2, cost_m=0, flags=['amplify'],
                     fission_level=1, fusion_level=1, hits=1, copy_count=0, charge_value=0,
                     swift_value=0, magic_swift_value=0, effect_text='', description=''),
    'Basic': dict(id='Basic', def_id='Basic', name='基础', name_cn='基础', name_en='Basic',
                  card_type='thorn', cost_e=1, cost_m=0, flags=['temp_swift'],
                  fission_level=1, fusion_level=1, hits=1, copy_count=0, charge_value=0,
                  swift_value=0, magic_swift_value=0, effect_text='', description=''),
}

html = (
    '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body><div id="probe"></div>'
    '<script>window.__G__={errors:[]};window.onerror=function(m,s,l){window.__G__.errors.push(m+"@"+l)};'
    'window.fetch=function(){return Promise.reject(new Error("offline"))};'
    'window.WebSocket=function(){throw new Error("offline")};</script>'
    '<script>\n' + game_js + '\n</script>'
    '<script>CARD_DEFS = ' + repr(defs).replace("'", '"').replace('True', 'true').replace('False', 'false') + ';\n'
    'try {\n'
    '  const flags = getAllGalleryFlags();\n'
    '  window.__G__.gallery = {\n'
    '    tempHidden: !flags.includes("temp_swift") && !flags.includes("temp_heavy") && !flags.includes("temp_magic_heavy"),\n'
    '    unfadingSingle: flags.filter(f => f === "unfading").length === 1 && !flags.includes("unfading_power") && !flags.includes("unfading_fission"),\n'
    '    label: getFlagLabel("unfading"),\n'
    '    hasColor: !!CARD_FLAG_TERM_COLORS.unfading && !!CARD_FLAG_STYLES.unfading,\n'
    '    powerColor: CARD_FLAG_TERM_COLORS.unfading_power === CARD_FLAG_TERM_COLORS.unfading_fission,\n'
    '    users: getGalleryFlagUsers("unfading").map(c => c.id).sort(),\n'
    '    descOk: (getIntroFlagDescription("unfading") || "").indexOf("留存位") >= 0,\n'
    '    magicHeavyDesc: (getIntroFlagDescription("magic_heavy") || "").length > 0,\n'
    '  };\n'
    '} catch (e) { window.__G__.gallery = { error: String(e) }; }\n'
    'document.getElementById("probe").textContent = JSON.stringify(window.__G__);</script>'
    '</body></html>'
)

page = OUT / 'smoke.html'
page.write_text(html, encoding='utf-8')
edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not Path(edge).exists():
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
res = subprocess.run([edge, '--headless=new', '--disable-gpu', '--dump-dom', '--virtual-time-budget=5000',
                      page.as_uri()], capture_output=True, timeout=90)
for line in res.stdout.decode('utf-8', 'ignore').splitlines():
    if 'id="probe"' in line and len(line) > 60:
        print(line[line.find('{'):].rsplit('</div>', 1)[0])
