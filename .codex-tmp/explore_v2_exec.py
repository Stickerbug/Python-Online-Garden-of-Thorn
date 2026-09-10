# -*- coding: utf-8 -*-
import io, re, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

rt = open("mod_runtime_v2.py", encoding="utf-8").read()
print("lines:", len(rt.splitlines()))
for m in re.finditer(r"^def ([A-Za-z0-9_]+)\(", rt, re.M):
    print("  def", m.group(1))
print("--- _atomic_ references ---")
for line_no, line in enumerate(rt.splitlines(), 1):
    if "_atomic_" in line or "run_step" in line or "execute_step" in line:
        print(line_no, "|", line.strip()[:150])
