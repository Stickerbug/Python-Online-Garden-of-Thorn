# -*- coding: utf-8 -*-
"""Round 108 / 批次 DF：状态 id 的发布期提示。

官方 17 条状态内置化（`official_statuses.py`）之后：

* 官方命名空间里写了内置表没有的状态 id → 基本是拼错，给提示（运行时静默无效）；
* 官方包再声明内置状态 → 提示"可以删掉"；
* 第三方包的状态短名与内置状态撞名 → 提示（短名查找会先命中内置那条）；
* 第三方命名空间（不在词表里）→ **不提示**，避免误伤跨模组引用。
"""

from __future__ import annotations

from mod_validator_v2 import validate_mod_v2


def _package(status_value: str, *, declare: str = "", namespace: str = "probe") -> dict:
    statuses = []
    if declare:
        statuses.append({"id": f"{namespace}:{declare}", "name_cn": declare})
    return {
        "format_version": 2,
        "manifest": {"id": namespace, "name": "Probe", "version": "1.0.0",
                     "api_version": "2.0", "capabilities": ["cards", "statuses", "logic.basic"]},
        "registries": {
            "cards": [{
                "id": f"{namespace}:probe_card",
                "name_cn": "探针卡",
                "effect_text": "探针",
                "type": "bloom",
                "cost_e": 1,
                "count": 1,
                "events": {"on_play": {"steps": [
                    {"op": "status_op", "action": "add", "status": status_value, "amount": 1,
                     "target": "target", "log": False}
                ]}},
            }],
            "statuses": statuses,
            "tags": [],
            "opening_events": [],
            "ui_components": [],
        },
        "patches": [],
        "compatibility": [],
        "event_hooks": [],
        "locales": {"zh": {"manifest": {"name": "探针", "description": "探针"},
                           "cards": {f"{namespace}:probe_card": {
                               "name": "探针卡", "effect_text": "探针", "description": "探针"}}}},
    }


def _warnings(data: dict) -> list:
    result = validate_mod_v2(data)
    assert not result.errors, result.errors
    return [item for item in result.warnings if "状态" in item]


def test_typo_in_official_namespace_is_reported():
    found = _warnings(_package("jungle:sheild"))
    assert len(found) == 1
    assert "jungle:sheild" in found[0]


def test_builtin_status_reference_is_clean():
    assert _warnings(_package("jungle:shield")) == []


def test_chinese_status_name_is_not_reported():
    assert _warnings(_package("眩晕")) == []


def test_third_party_namespaces_are_not_reported():
    assert _warnings(_package("othermod:thing")) == []
    assert _warnings(_package("probe:mine", declare="mine")) == []


def test_redeclaring_a_builtin_status_is_reported():
    data = _package("arctic:frost", declare="frost", namespace="arctic")
    found = [item for item in validate_mod_v2(data).warnings if "内置状态" in item]
    assert len(found) == 1
    assert "arctic:frost" in found[0]


def test_short_name_collision_is_reported():
    data = _package("mymod:shield", declare="shield", namespace="mymod")
    found = [item for item in validate_mod_v2(data).warnings if "短名" in item]
    assert len(found) == 1
    assert "jungle:shield" in found[0]


def test_official_packages_are_clean():
    """20 个官方包一个状态提示都不该有（防止误报）。"""

    import json
    import pathlib
    import zipfile

    root = pathlib.Path(__file__).resolve().parents[1]
    for path in sorted((root / "mods").glob("*.gtnmod")):
        with zipfile.ZipFile(path) as archive:
            payload = json.loads(archive.read("mod.json").decode("utf-8-sig"))
        result = validate_mod_v2(payload, source=path.name, allow_reserved_namespaces=True)
        hits = [item for item in result.warnings
                if "状态 id" in item or "内置状态" in item or "短名" in item]
        assert hits == [], f"{path.name}: {hits}"
