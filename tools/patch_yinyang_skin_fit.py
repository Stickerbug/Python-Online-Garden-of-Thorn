# -*- coding: utf-8 -*-
"""阴阳/阴阳玉皮肤图适配：正方形满幅图按卡面 63:88 安全区缩放居中。

原 SVG 1133.86×1133.86 满幅内容，经 .card-skin-under 的 182.3% 宽渲染后
上下各溢出卡高 ~15%，不透明内容盖住相邻行（#307）且满幅构图与卡文字
冲突（#309）。包一层嵌套 svg：外层画布保持正方形（与渲染契约一致），
原内容缩至中部 71.6% 高度垂直居中，上下留透明——溢出区透明不再遮挡，
内容完整显示。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / 'static/assets/card-skins/front/阴阳.svg',
    ROOT / 'static/assets/card-skins/front/阴阳玉.svg',
    ROOT / 'static/assets/card-skins/back/阴阳.svg',
    ROOT / 'static/assets/card-skins/back/阴阳玉.svg',
]
CANVAS = 1133.86
SAFE_H = CANVAS * (63.0 / 88.0)     # 810.38：63:88 安全区高
OFFSET_Y = (CANVAS - SAFE_H) / 2    # 161.74

for path in FILES:
    src = path.read_text(encoding='utf-8')
    if 'skin-fit-wrapper' in src:
        print(f'{path.name}: 已处理，跳过')
        continue
    # 找根 <svg ...> 标签
    m = re.search(r'<svg\b[^>]*>', src)
    if not m:
        print(f'{path.name}: 无根 svg，跳过'); continue
    root_tag = m.group(0)
    if 'viewBox' not in root_tag:
        print(f'{path.name}: 根无 viewBox，跳过'); continue
    head = src[:m.start()]
    inner = src[m.end():]
    # 原根降级为嵌套 svg：去掉 width/height（用外层给定的 x/y/width/height）
    nested = re.sub(r'\s(width|height)="[^"]*"', '', root_tag, count=2)
    nested = nested.replace('<svg', f'<svg x="0" y="{OFFSET_Y:.2f}" width="{CANVAS}" height="{SAFE_H:.2f}"', 1)
    new = (
        head
        + f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS} {CANVAS}">\n'
        + '<!-- skin-fit-wrapper: 原图缩放居中于 63:88 安全区，上下留透明防溢出遮挡 -->\n'
        + nested + inner
    )
    path.write_text(new, encoding='utf-8', newline='\n')
    print(f'{path.parent.name}/{path.name}: 已包裹（安全区高 {SAFE_H:.1f}）')
