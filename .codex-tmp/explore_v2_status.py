# -*- coding: utf-8 -*-
import io, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

src = open("game_engine.py", encoding="utf-8").read()
for needle in ("    def _get_v2_status_def(", "    def _v2_hooks_for(", "    def _run_v2_play_hook("):
    idx = src.find(needle)
    print("=====", needle)
    print(src[idx:idx + 1400])
