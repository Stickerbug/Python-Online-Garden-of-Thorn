# -*- coding: utf-8 -*-
import io, sys, pathlib, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

for path in ("game_engine.py", "game_engine_2v2.py", "game_engine_urf.py", "app.py", "mod_runtime_v2.py"):
    src = open(path, encoding="utf-8").read()
    for m in re.finditer(r"\.(v2_status_defs|v2_event_hooks|v2_loadout|v2_tag_defs|v2_mod_ids)\s*=", src):
        line_start = src.rfind("\n", 0, m.start()) + 1
        line_end = src.find("\n", m.start())
        print("%-22s %s" % (path, src[line_start:line_end].strip()[:140]))
