# -*- coding: utf-8 -*-
import io, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

src = open("game_engine.py", encoding="utf-8").read()
for m in __import__("re").finditer(r"same_name", src):
    start = src.rfind("\n", 0, m.start() - 200) 
    line_no = src.count("\n", 0, m.start()) + 1
    line_start = src.rfind("\n", 0, m.start()) + 1
    line_end = src.find("\n", m.start())
    print(line_no, "|", src[line_start:line_end].strip()[:160])
