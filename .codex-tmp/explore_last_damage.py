# -*- coding: utf-8 -*-
import io, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

src = open("mod_runtime_v2.py", encoding="utf-8").read()
marker = 'last_damage'
start = 0
while True:
    index = src.find('"%s"' % marker, start)
    if index < 0:
        break
    print("---", index)
    print(src[max(0, index - 260):index + 420])
    start = index + 1
