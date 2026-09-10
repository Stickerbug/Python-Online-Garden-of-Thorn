# -*- coding: utf-8 -*-
"""List the ops the v2 runtime understands plus the engine atom inventory."""

import io
import re
import sys
import pathlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

rt = open("mod_runtime_v2.py", encoding="utf-8").read()
print("--- mod_runtime_v2 op names ---")
names = sorted(set(re.findall(r"_ops?\[[\"']([A-Za-z0-9_:]+)[\"']\]", rt))
               | set(re.findall(r"op(?:_name)?\s*==\s*[\"']([A-Za-z0-9_:]+)[\"']", rt)))
print(len(names))
for name in names:
    print("   ", name)

print("--- mod_spec_v2 declared ops ---")
spec = open("mod_spec_v2.py", encoding="utf-8").read()
for match in re.finditer(r"^([A-Z_]+)\s*=\s*\(([^)]*)\)", spec, re.M):
    name, body = match.group(1), match.group(2)
    items = re.findall(r"[\"']([^\"']+)[\"']", body)
    if items and ("op" in name.lower() or "effect" in name.lower() or "step" in name.lower()):
        print(name, len(items))
