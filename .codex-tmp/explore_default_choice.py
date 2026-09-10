# -*- coding: utf-8 -*-
import io, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

src = open("game_engine.py", encoding="utf-8").read()
idx = src.find("    def _default_choice_for_pending(")
print(src[idx:idx + 2600])
print("==== default auto target ====")
idx = src.find("    def _default_auto_target_choice(")
print(src[idx:idx + 2000])
