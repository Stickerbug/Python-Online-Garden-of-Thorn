# -*- coding: utf-8 -*-
"""Full row context for colored cells in 卡牌数据10.xlsx."""
import sys, io, glob, os, zipfile
import xml.etree.ElementTree as ET
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

os.chdir(r"E:\Garden of Thorn 荆棘花园\开发表格")
path = glob.glob("Garden of Thorn 卡牌数据10.xlsx")[0]
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
M = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

z = zipfile.ZipFile(path)
styles_xml = ET.fromstring(z.read('xl/styles.xml'))
fills = []
for fill in styles_xml.findall('m:fills/m:fill', NS):
    color = None
    pat = fill.find('m:patternFill', NS)
    if pat is not None:
        fg = pat.find('m:fgColor', NS)
        if fg is not None:
            if fg.get('rgb'):
                color = fg.get('rgb')
            elif fg.get('theme') is not None:
                color = 'theme%s-%s' % (fg.get('theme'), fg.get('tint'))
    fills.append(color)
cell_xfs = [xf.get('fillId') for xf in styles_xml.findall('m:cellXfs/m:xf', NS)]

shared = []
if 'xl/sharedStrings.xml' in z.namelist():
    ss = ET.fromstring(z.read('xl/sharedStrings.xml'))
    for si in ss.findall('m:si', NS):
        shared.append(''.join(t.text or '' for t in si.iter(M + 't')))

wb = ET.fromstring(z.read('xl/workbook.xml'))
rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
rel_map = {rel.get('Id'): rel.get('Target') for rel in rels}

def col_num(ref):
    letters = ''.join(ch for ch in ref if ch.isalpha())
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n

SKIP = ['爬塔生物变种（先不做）']
for sheet in wb.findall('m:sheets/m:sheet', NS):
    name = sheet.get('name')
    if name in SKIP:
        continue
    rid = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
    target = rel_map[rid]
    if not target.startswith('xl/'):
        target = 'xl/' + target.lstrip('/')
    sheet_xml = ET.fromstring(z.read(target))
    rows = {}
    colored_rows = set()
    for c in sheet_xml.iter(M + 'c'):
        s = c.get('s')
        ref = c.get('r')
        rownum = int(''.join(ch for ch in ref if ch.isdigit()))
        v = c.find('m:v', NS)
        isn = c.find('m:is', NS)
        val = ''
        if c.get('t') == 's' and v is not None:
            val = shared[int(v.text)]
        elif c.get('t') == 'inlineStr' and isn is not None:
            val = ''.join(t.text or '' for t in isn.iter(M + 't'))
        elif v is not None:
            val = v.text or ''
        rows.setdefault(rownum, {})[col_num(ref)] = val
        if s is not None:
            fill_idx = int(cell_xfs[int(s)])
            rgb = fills[fill_idx] if fill_idx is not None and fill_idx < len(fills) else None
            if rgb and rgb not in ('00000000', 'FFFFFFFF', 'FFFFFF', 'none'):
                colored_rows.add(rownum)
    if colored_rows:
        maxcol = max((max(r.keys()) for r in rows.values() if r), default=0)
        print(f"\n{'='*90}\n### SHEET: {name}  colored rows: {sorted(colored_rows)}")
        for rn in sorted(colored_rows):
            cells = rows.get(rn, {})
            parts = []
            for cn in range(1, maxcol + 1):
                parts.append(cells.get(cn, ''))
            print(f"R{rn}: " + ' | '.join(parts))
