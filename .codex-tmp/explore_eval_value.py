# -*- coding: utf-8 -*-
import io, re, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

src = open("mod_runtime_v2.py", encoding="utf-8").read()
start = src.find("def eval_v2_value")
seg = src[start:start + 9000]
for match in re.finditer(r'op in \(([^)]*)\)|op == "([a-z_]+)"', seg):
    print(match.group(0)[:150])
print("---- get ----")
index = seg.find('"get"')
print(seg[max(0, index - 500):index + 800])
