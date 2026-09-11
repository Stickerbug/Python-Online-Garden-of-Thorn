# -*- coding: utf-8 -*-
"""把当前引擎原子按语义族分组并显示卡数据用量（只读，可复现）。

    python tools/family_inventory.py            # 人读清单
    python tools/family_inventory.py --json     # 机器可读

口径与 ``tools/mod_atom_report.py`` 一致：原子 = ``atomic_registry.engine_atomic_ops()``
（``game_engine*.py`` 里的 ``_atomic_*`` 处理器），用量 = 官方包 ``mod.json`` 里
``"op": "<name>"`` 的出现次数（含 ``type`` 写法——那是运行时/引擎都会拦的旧编码）。

Round 31 / 批次 Z 起本脚本进 ``tools/``（以前只在 ``.codex-tmp`` 里）。
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import atomic_registry  # noqa: E402
import mod_spec_v2  # noqa: E402

FAMILIES = (
    ("状态", ("status", "poison", "toxic", "burn", "frost", "fragile", "blind", "dizzy",
              "stagnation", "fracture", "sluggish", "vulnus", "vulnerable", "corruption",
              "invincible", "untargetable", "protection", "layer")),
    ("伤害", ("damage", "attack", "lifesteal", "ricochet", "crit", "power", "fission",
              "burn_damage", "counter", "absorb")),
    ("区域/给牌", ("move", "give", "draw", "discard", "exile", "deck", "hand", "steal",
                   "put_card", "shuffle", "reveal")),
    ("装备", ("equip", "durability", "seal", "sealed")),
    ("属性/资源", ("prop", "resource", "elixir", "magic", "armor", "health", "cost",
                   "var", "counter", "charge", "stat")),
    ("标签", ("tag",)),
    ("控制流", ("if", "for_each", "repeat", "once", "break", "continue", "after_all",
                "random", "choose", "timed", "listener")),
    ("时点/监听", ("timed", "turn", "listener", "timer", "countdown", "queue", "auto_play",
                   "on_")),
)


def family_of(name: str) -> str:
    for label, keys in FAMILIES:
        if any(key in name for key in keys):
            return label
    return "其它"


def usage_map() -> collections.Counter:
    atoms = sorted(atomic_registry.engine_atomic_ops())
    usage: collections.Counter = collections.Counter()
    for package in sorted((ROOT / "mods").glob("*.gtnmod")):
        with zipfile.ZipFile(package) as archive:
            text = json.dumps(json.loads(archive.read("mod.json")), ensure_ascii=False)
        for name in atoms:
            usage[name] += len(re.findall(r'"op"\s*:\s*"%s"' % re.escape(name), text))
    return usage


def inventory() -> dict:
    atoms = sorted(atomic_registry.engine_atomic_ops())
    core = set(mod_spec_v2._CORE_LOGIC_OPS or ())
    usage = usage_map()
    groups: dict[str, list[str]] = collections.defaultdict(list)
    for name in atoms:
        groups[family_of(name)].append(name)
    return {
        "engine_atoms": atoms,
        "core_ops": len(core),
        "registered": sum(1 for name in atoms if name in core),
        "families": {label: groups.get(label) or [] for label, _keys in FAMILIES} | {"其它": groups.get("其它") or []},
        "usage": {name: usage.get(name, 0) for name in atoms},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="引擎原子语义族 + 用量（只读）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    data = inventory()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True))
        return 0
    print("引擎原子 %d（登记在策展清单的 %d）\n" % (len(data["engine_atoms"]), data["registered"]))
    for label, members in data["families"].items():
        if not members:
            continue
        print("== %s（%d）==" % (label, len(members)))
        for name in members:
            print("   %-38s 用量 %d" % (name, data["usage"][name]))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
