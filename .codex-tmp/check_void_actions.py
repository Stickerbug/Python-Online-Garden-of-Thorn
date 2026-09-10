# -*- coding: utf-8 -*-
import io, re, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

src = open("void_dlc_runtime.py", encoding="utf-8").read()
start = src.find("def _run_simple_action")
end = src.find("\ndef ", start + 10)
body = src[start:end]
print("remaining branches:", sorted(set(re.findall(r'action == "([a-z_0-9]+)"', body))))
print("combined branches:", re.findall(r"action in \(([^)]*)\)", body))
print("fan_turn_start present:", "fan_turn_start" in body)
