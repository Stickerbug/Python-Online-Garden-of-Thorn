# -*- coding: utf-8 -*-
import io, re, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

src = open("tools/refactor_card_atoms.py", encoding="utf-8").read()
for m in re.finditer(r'^    "([A-Za-z0-9_]+)":', src, re.M):
    print(m.group(1))
