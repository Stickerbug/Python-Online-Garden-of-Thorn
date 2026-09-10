# -*- coding: utf-8 -*-
import io, sys, pathlib, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

engine_files = ["game_engine.py", "game_engine_2v2.py", "game_engine_urf.py"]
src = "\n".join(open(f, encoding="utf-8").read() for f in engine_files)
for name in ("respond_to_attack", "handle_response", "use_response", "respond("):
    for m in re.finditer(re.escape("def %s" % name), src):
        print(m.start(), name)
print([n for n in sorted(set(re.findall(r"^    def ([a-z_]*respons[a-z_]*)", src, re.M)))])
print([n for n in sorted(set(re.findall(r"^    def ([a-z_]*counter[a-z_]*)", src, re.M)))])
idx = src.find("    def _public_pending_response(")
print(src[idx:idx + 1500])
