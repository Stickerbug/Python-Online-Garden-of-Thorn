# -*- coding: utf-8 -*-
"""双加数体系渲染冒烟：自包含 HTML 注入全量 game.js，渲染代表性卡面并截图+断言芯片文本。"""
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(r'C:\Users\bug\AppData\Local\Temp\dual_addend_smock')
OUT.mkdir(exist_ok=True)

game_js = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')

# 代表性场景：珊瑚(不灭:裂变+裂变4+1)、锯片(裂变2回落)、绿石竹(威力:3+2 带不灭:威力)、
# 琥珀(威力:0-9)、迅捷合并(迅捷:2+1)、魔沉(魔力沉重:0+2)、裂变1+1、聚变3
cards = [
    dict(def_id='Coral', instance_id=1, fission_level=5, fission_base=4),
    dict(def_id='Sawblade', instance_id=2, fission_level=3, fission_base=2),
    dict(def_id='Dianthus', instance_id=3, power_value=5, power_base=3),
    dict(def_id='Amber', instance_id=4, power_value=-9, power_base=0),
    dict(def_id='Basic', instance_id=5, swift_value=2, temp_swift_value=1, heavy_value=1, temp_heavy_value=2, temp_magic_heavy_value=2),
    dict(def_id='Basic', instance_id=6, fission_level=2, fission_base=1),
    dict(def_id='FusionCard', instance_id=7, fusion_level=4, fusion_base=3),
]

defs = {}
for cid, ctype in (('Coral', 'thorn'), ('Sawblade', 'thorn'), ('Dianthus', 'thorn'), ('Amber', 'thorn'), ('Basic', 'thorn'), ('FusionCard', 'thorn')):
    defs[cid] = dict(id=cid, def_id=cid, name='测试' + cid, name_cn='测试' + cid, name_en='T' + cid,
                     card_type=ctype, cost_e=1, cost_m=0, flags=['preserve_fission'] if cid == 'Coral' else (['amplify'] if cid == 'Dianthus' else []),  # 旧名数据，验证别名归一
                     fission_level=4 if cid == 'Coral' else (2 if cid == 'Sawblade' else 1),
                     fusion_level=3 if cid == 'FusionCard' else 1, hits=1, copy_count=0, charge_value=0,
                     swift_value=0, magic_swift_value=0, effect_text='', description='')

html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<link rel="stylesheet" href="file:///{(ROOT / 'static' / 'css' / 'style.css').as_posix()}">
<style>body{{background:#222;color:#eee;font-family:sans-serif;padding:16px}} .hand{{display:flex;flex-wrap:wrap;gap:12px}}</style>
</head><body>
<div id="hand" class="hand"></div>
<div id="probe"></div>
<script>
window.__SMOKE__ = {{ errors: [] }};
window.onerror = function(msg, src, line) {{ window.__SMOKE__.errors.push(msg + '@' + line); }};
// 阻断网络
window.fetch = function() {{ return Promise.reject(new Error('offline')); }};
window.WebSocket = function() {{ throw new Error('offline'); }};
</script>
<script>
{game_js}
</script>
<script>
CARD_DEFS = {json.dumps(defs, ensure_ascii=False)};
const HAND = {json.dumps(cards, ensure_ascii=False)};
const host = document.getElementById('hand');
window.__SMOKE__.chips = [];
for (const c of HAND) {{
    try {{
        const el = createCardElement(c, {{}});
        host.appendChild(el);
        const chips = Array.from(el.querySelectorAll('.card-flag')).map(s => s.textContent.trim());
        window.__SMOKE__.chips.push({{ id: c.def_id + '#' + c.instance_id, chips }});
    }} catch (e) {{
        window.__SMOKE__.chips.push({{ id: c.def_id + '#' + c.instance_id, error: String(e) }});
    }}
}}
document.getElementById('probe').textContent = JSON.stringify(window.__SMOKE__);
</script>
</body></html>'''

page = OUT / 'smoke.html'
page.write_text(html, encoding='utf-8')
shot = OUT / 'smoke.png'
edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not Path(edge).exists():
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
subprocess.run([edge, '--headless=new', '--disable-gpu', f'--screenshot={shot}', '--window-size=1400,900',
                f'--virtual-time-budget=6000', page.as_uri()], capture_output=True, timeout=90)
time.sleep(1)
print('screenshot exists:', shot.exists(), shot.stat().st_size if shot.exists() else 0)
print('page:', page)
