# -*- coding: utf-8 -*-
import io, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

src = open("game_engine.py", encoding="utf-8").read()
idx = src.find("    def handle_response(")
print(src[idx:idx + 2500])
print("===== pending_response construction =====")
for marker in ("self.pending_response = {", "'counter_cards':"):
    start = 0
    count = 0
    while count < 3:
        i = src.find(marker, start)
        if i < 0:
            break
        print("---", marker, i)
        print(src[max(0, i - 400):i + 500])
        start = i + 1
        count += 1
