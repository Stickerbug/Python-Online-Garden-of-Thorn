# -*- coding: utf-8 -*-
import io, json, pathlib, sys, zipfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parents[1]
package = ROOT / "mods" / (sys.argv[1] if len(sys.argv) > 1 else "Desert Cards Addition.gtnmod")
with zipfile.ZipFile(package) as archive:
    names = [n for n in archive.namelist() if n.endswith(".json")]
    print("json files:", names)
    spec = json.loads(archive.read("mod.json"))
print("top keys:", list(spec.keys()))
print("registries keys:", list((spec.get("registries") or {}).keys()))
cards = (spec.get("registries") or {}).get("cards")
print("cards type:", type(cards).__name__, "len:", len(cards) if hasattr(cards, "__len__") else "-")
sample_key = list(cards)[0] if isinstance(cards, dict) else 0
sample = cards[sample_key] if isinstance(cards, dict) else cards[0]
print("sample:", json.dumps(sample, ensure_ascii=False)[:1500])
