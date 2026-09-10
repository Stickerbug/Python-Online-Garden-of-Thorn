# -*- coding: utf-8 -*-
"""List card-specific engine atoms that no card data and no engine code uses."""

import io, json, pathlib, re, sys, zipfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PREFIXES = ("arctic", "bio", "desert", "garden", "jungle", "jurassic",
            "ocean", "sewers", "void", "hel", "factory", "vanilla")
ENGINE_FILES = ("game_engine.py", "game_engine_2v2.py", "game_engine_urf.py")
PY_FILES = sorted(ROOT.glob("*.py"))

atoms = set()
for name in ENGINE_FILES:
    atoms |= set(re.findall(r"def _atomic_([A-Za-z0-9_]+)\(", (ROOT / name).read_text(encoding="utf-8")))

used_ops = set()
for package in (ROOT / "mods").glob("*.gtnmod"):
    with zipfile.ZipFile(package) as archive:
        spec = json.loads(archive.read("mod.json"))
    used_ops |= set(re.findall(r'"op"\s*:\s*"([A-Za-z0-9_:]+)"', json.dumps(spec, ensure_ascii=False)))

sources = {path.name: path.read_text(encoding="utf-8", errors="replace") for path in PY_FILES}
dead = []
for atom in sorted(atoms):
    if atom.split("_")[0] not in PREFIXES:
        continue
    if atom in used_ops:
        continue
    callers = 0
    for name, text in sources.items():
        for match in re.finditer(r"_atomic_%s\(" % re.escape(atom), text):
            head = text.rfind("\n", 0, match.start()) + 1
            if text[head:match.start()].strip().startswith("def "):
                continue
            callers += 1
    if not callers:
        dead.append(atom)
print("dead card-specific atoms:", len(dead))
for atom in dead:
    print("   ", atom)
