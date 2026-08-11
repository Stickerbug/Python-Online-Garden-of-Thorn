import json
import os
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"


def mark_package(path: Path) -> bool:
    with zipfile.ZipFile(path, "r") as archive:
        entries = [(info, archive.read(info.filename)) for info in archive.infolist()]

    changed = False
    rewritten = []
    for info, content in entries:
        if info.filename == "mod.json":
            document = json.loads(content.decode("utf-8-sig"))
            manifest = document.setdefault("manifest", {})
            if manifest.get("category") != "entertainment":
                manifest["category"] = "entertainment"
                content = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
                changed = True
        rewritten.append((info, content))

    if not changed:
        return False

    handle, temporary_name = tempfile.mkstemp(suffix=".gtnmod", dir=path.parent)
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w") as archive:
            for info, content in rewritten:
                archive.writestr(info, content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def main():
    packages = sorted(MODS.glob("*DLC*.gtnmod"))
    changed = [path.name for path in packages if mark_package(path)]
    print(f"DLC packages checked: {len(packages)}; updated: {len(changed)}")
    for name in changed:
        print(name)


if __name__ == "__main__":
    main()
