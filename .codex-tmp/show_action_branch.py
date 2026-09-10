# -*- coding: utf-8 -*-
import io, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

src = open("void_dlc_runtime.py", encoding="utf-8").read()
for action in sys.argv[1:]:
    marker = 'action == "%s"' % action
    start = src.find(marker)
    print("=" * 30, action, start)
    if start < 0:
        continue
    end = src.find('elif action', start)
    print(src[start:end if end > 0 else start + 1200])
