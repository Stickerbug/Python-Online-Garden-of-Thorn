# -*- coding: utf-8 -*-
import io, sys, pathlib, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

for path in ("game_engine.py", "game_engine_2v2.py", "game_engine_urf.py", "mod_runtime_v2.py"):
    src = open(path, encoding="utf-8").read()
    hits = sorted(set(re.findall(r"pending_v2_ui", src)))
    print(path, len(hits))
    for m in re.finditer(r"^    def ([A-Za-z0-9_]+)\(", src, re.M):
        pass
    names = sorted(set(re.findall(r"def ([a-z_0-9]*v2_ui[a-z_0-9]*)", src)))
    print("   funcs:", names)

src = open("game_engine.py", encoding="utf-8").read()
for m in re.finditer(r"pending_v2_ui", src):
    i = m.start()
    line_start = src.rfind("\n", 0, i) + 1
    print("  >>", src[line_start:src.find("\n", i)].strip()[:150])
