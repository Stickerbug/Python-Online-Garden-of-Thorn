# -*- coding: utf-8 -*-
import io, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

src = open("game_engine.py", encoding="utf-8").read()
needle = "    def handle_v2_ui_response("
idx = src.find(needle)
print(src[idx:idx + 1500])
print("==== validate ====")
rt = open("mod_runtime_v2.py", encoding="utf-8").read()
needle2 = "def validate_v2_ui_response("
j = rt.find(needle2)
print(rt[j:j + 1200])
