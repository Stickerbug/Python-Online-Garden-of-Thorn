# -*- coding: utf-8 -*-
import io, re, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

src = open("game_engine.py", encoding="utf-8").read()
print("quoted choice_type:", sorted(set(re.findall(r"'choice_type':\s*'?([A-Za-z_]+)'?", src))))
print("assign choice_type:", sorted(set(re.findall(r"\['choice_type'\]\s*=\s*'?([A-Za-z_]+)'?", src))))
print("keys of queued choice:")
idx = src.find("    def _queue_card_choice(")
print(src[idx:idx + 1800])
