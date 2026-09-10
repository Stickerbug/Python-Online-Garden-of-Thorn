# -*- coding: utf-8 -*-
import io, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

src = open("game_engine.py", encoding="utf-8").read()
markers = ("choose_cards_from_hand", "choose_same_attacks_from_hand")
count = 0
for index, line in enumerate(src.splitlines(), 1):
    if any(marker in line for marker in markers):
        print(index, "|", line.strip()[:170])
        count += 1
print("total lines:", count)
