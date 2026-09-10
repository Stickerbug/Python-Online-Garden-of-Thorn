# -*- coding: utf-8 -*-
import io, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import mod_runtime_v2 as rt

print("ADVANCED_ATOMIC_OPS:", len(rt.ADVANCED_ATOMIC_OPS))
for name in sorted(rt.ADVANCED_ATOMIC_OPS):
    print("   ", name)
print("ALIASES:", len(rt.ATOMIC_OP_ALIASES))
for key, value in sorted(rt.ATOMIC_OP_ALIASES.items()):
    print("   %s -> %s" % (key, value))
