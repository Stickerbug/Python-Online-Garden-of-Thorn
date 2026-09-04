# -*- coding: utf-8 -*-
"""Dump one sheet fully (all rows) from the workbook."""
import sys, io, glob, os, zipfile
import xml.etree.ElementTree as ET
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

os.chdir(r"E:\Garden of Thorn 荆棘花园\开发表格")
path = glob.glob("Garden of Thorn 卡牌数据10.xlsx")[0]
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
M = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

z = zipfile.ZipFile(path)
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

want = sys.argv[1] if len(sys.argv) > 1 else '附魔书设计'
for sheet in wb.findall('m:sheets/m:sheet', NS):
    name = sheet.get('name')
    if name != want:
        continue
    rid = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
    target = rel_map[rid]
    if not target.startswith('xl/'):
        target = 'xl/' + target.lstrip('/')
    sheet_xml = ET.fromstring(z.read(target))
    rows = {}
    for c in sheet_xml.iter(M + 'c'):
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
        if val:
            rows.setdefault(rownum, {})[col_num(ref)] = val
    maxcol = max((max(r.keys()) for r in rows.values() if r), default=0)
    for rn in sorted(rows):
        cells = rows[rn]
        parts = [cells.get(cn, '') for cn in range(1, maxcol + 1)]
        print(f"R{rn}: " + ' | '.join(parts))
