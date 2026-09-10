# -*- coding: utf-8 -*-
import io, sys, pathlib, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

src = open("app.py", encoding="utf-8").read()
for m in re.finditer(r"(GameEngine2v2|GameEngineURF|GameEngine)\(", src):
    line_start = src.rfind("\n", 0, m.start()) + 1
    line_end = src.find("\n", m.start())
    print(src[line_start:line_end].strip()[:160])
