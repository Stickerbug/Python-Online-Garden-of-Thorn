# -*- coding: utf-8 -*-
"""STS2 动画提速+流畅度改造冒烟：无头 Edge 验证 WAAPI 飞行、时长减半、动画完成。"""
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(r'C:\Users\bug\AppData\Local\Temp\sts2_motion_smoke')
OUT.mkdir(exist_ok=True)

motion = (ROOT / 'static' / 'js' / 'sts2_motion.js').read_text(encoding='utf-8')
css_uri = (ROOT / 'static' / 'css' / 'sts2_motion.css').as_uri()

html = (
    '<!DOCTYPE html><html><head><meta charset="utf-8">'
    f'<link rel="stylesheet" href="{css_uri}">'
    '<style>body{background:#222} #a,#b{position:fixed;width:60px;height:84px;background:#556}'
    ' #a{left:100px;top:300px} #b{right:80px;top:120px}</style></head><body>'
    '<div id="a"></div><div id="b"></div><div id="probe"></div>'
    '<script>\n'
    'window.__S__ = { errors: [], done: [] };\n'
    'window.onerror = function(m, s, l) { window.__S__.errors.push(m + "@" + l); };\n'
    'const probe = document.getElementById("probe");\n'
    'const flush = () => { probe.textContent = JSON.stringify(window.__S__); };\n'
    'let trailMax = 0;\n'
    'setInterval(function () {\n'
    '  const n = document.querySelectorAll(".sts2-trail-card").length;\n'
    '  if (n > trailMax) { trailMax = n; window.__S__.trailMax = n; }\n'
    '}, 16);\n'
    '</script>\n'
    '<script>\n' + motion + '\n</script>\n'
    '<script>\n'
    '(async function () {\n'
    '  const t0 = performance.now();\n'
    '  const T = STS2.TIMING;\n'
    '  window.__S__.timing = { DRAW_FLY: T.DRAW_FLY, PLAY_FLY: T.PLAY_FLY, DISCARD_FLY: T.DISCARD_FLY, SHUFFLE_FLY: T.SHUFFLE_FLY };\n'
    '  flush();\n'
    '  try {\n'
    '    await STS2.flyCard({ from: "#a", to: "#b", cardBack: true, trailColor: "#a08050" });\n'
    '    window.__S__.done.push("flyCard ms=" + Math.round(performance.now() - t0));\n'
    '    flush();\n'
    '    const t1 = performance.now();\n'
    '    const r = document.getElementById("b").getBoundingClientRect();\n'
    '    await STS2.drawToHand({ pileEl: "#a", slots: [r, r, r] });\n'
    '    window.__S__.done.push("drawToHand ms=" + Math.round(performance.now() - t1));\n'
    '    flush();\n'
    '  } catch (e) {\n'
    '    window.__S__.errors.push("async: " + String(e && e.stack || e));\n'
    '    flush();\n'
    '  }\n'
    '})();\n'
    '</script></body></html>'
)

page = OUT / 'smoke.html'
page.write_text(html, encoding='utf-8')
edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not Path(edge).exists():
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
for attempt in range(2):
    res = subprocess.run([edge, '--headless=new', '--disable-gpu', '--dump-dom', '--window-size=900,700',
                          '--virtual-time-budget=8000', page.as_uri()], capture_output=True, timeout=90)
    out = res.stdout.decode('utf-8', 'ignore')
    for line in out.splitlines():
        if 'id="probe"' in line and len(line) > 60:
            print(f'attempt {attempt + 1}:', line.strip()[:500])
    time.sleep(1)
