# -*- coding: utf-8 -*-
import io, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

src = open("mod_runtime_v2.py", encoding="utf-8").read()
start = src.find('    if op == "deal_damage":')
end = src.find('    if op in ("direct_damage"', start)
print(src[start:end])
