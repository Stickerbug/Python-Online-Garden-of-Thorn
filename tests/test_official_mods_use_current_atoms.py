"""官方模组包不能再用「已移除的原子」。

反馈 #186 的教训：批次 DD 把 ``player_status_layers`` 并进 ``status_op`` 并删除旧原子，
但 Ocean 包的黄瓜（``ocean:cucumber``）漏迁移了——上线后这张牌的「1层无法选中」直接报错失效。
这个测试扫描全部官方包的 ``mod.json``，任何 removed op 都会立刻失败。
"""

import json
import zipfile
from pathlib import Path

from mod_spec_v2 import REMOVED_ATOMIC_OPS

ROOT = Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"


def _collect_ops(value, found):
    if isinstance(value, dict):
        op = value.get("op")
        if isinstance(op, str):
            found.add(op)
        for item in value.values():
            _collect_ops(item, found)
    elif isinstance(value, list):
        for item in value:
            _collect_ops(item, found)


def _mod_json_ops(package_path: Path):
    with zipfile.ZipFile(package_path) as archive:
        data = json.loads(archive.read("mod.json").decode("utf-8-sig"))
    found = set()
    registries = data.get("registries") or {}
    for section in ("cards", "statuses", "tags", "relics", "enemies"):
        entries = registries.get(section) or []
        if isinstance(entries, dict):
            entries = list(entries.values())
        _collect_ops(entries, found)
    return data, found


def test_official_mods_do_not_use_removed_atomic_ops():
    offenders = []
    for package_path in sorted(MODS.glob("*.gtnmod")):
        data, ops = _mod_json_ops(package_path)
        removed = sorted(op for op in ops if op in REMOVED_ATOMIC_OPS)
        if removed:
            offenders.append(f"{package_path.name}: {removed}")
    assert offenders == [], (
        "官方模组仍在用已移除的原子（写这些 op 会在运行时直接报错）：" + "; ".join(offenders)
    )


def test_feedback_186_cucumber_uses_the_status_op_form():
    package = MODS / "Ocean Cards Addition.gtnmod"
    with zipfile.ZipFile(package) as archive:
        data = json.loads(archive.read("mod.json").decode("utf-8-sig"))
    card = next(card for card in data["registries"]["cards"] if card["id"] == "ocean:cucumber")
    steps = card["events"]["on_response"]["resolution"]["after_resolution"]
    assert steps == [
        {"op": "status_op", "action": "add", "status": "untargetable", "amount": 1},
    ]
