"""Tests for tools/mod_atom_report.py (read-only atom/card-data report)."""

import importlib.util
import json
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load_module():
    spec = importlib.util.spec_from_file_location(
        'mod_atom_report', ROOT / 'tools' / 'mod_atom_report.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


atom_report = _load_module()


def _write_package(path, payload):
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('mod.json', json.dumps(payload, ensure_ascii=False))
    return path


def test_walk_steps_collects_both_encodings_and_nested_containers():
    steps = [
        {"op": "deal_damage", "on_hit": [{"type": "apply_burn", "params": {"amount": 1}}]},
        {
            "type": "if",
            "params": {
                "then": [{"op": "heal"}],
                "else": [{"type": "log", "params": {}}],
            },
        },
    ]
    seen = []
    atom_report.walk_steps(
        steps, lambda step, op: seen.append((op, atom_report.is_legacy_encoding(step)))
    )

    assert [op for op, _ in seen] == ["deal_damage", "apply_burn", "if", "heal", "log"]
    assert [legacy for _, legacy in seen] == [False, True, True, False, True]


def test_conditions_and_ui_components_are_not_steps():
    steps = [
        {"op": "if", "condition": {"type": "card_has_modifier"}, "then": []},
        {
            "op": "request_ui",
            "component": {"type": "modal", "controls": [{"type": "select"}]},
        },
    ]
    seen = []
    atom_report.walk_steps(steps, lambda step, op: seen.append(op))

    assert seen == ["if", "request_ui"]


def test_package_scan_counts_steps_and_flags_legacy_encoding(tmp_path):
    payload = {
        "manifest": {"id": "demo", "default_language": "zh"},
        "registries": {
            "cards": [
                {
                    "id": "demo:alpha",
                    "events": {"on_play": {"steps": [{"op": "deal_damage"}]}},
                },
                {
                    "id": "demo:beta",
                    "events": {
                        "on_play": {
                            "steps": [{"type": "deal_damage", "params": {"amount": 2}}]
                        }
                    },
                },
            ]
        },
    }
    _write_package(tmp_path / "Demo.gtnmod", payload)

    report = atom_report.collect(tmp_path)
    summary = atom_report.build_summary(report)

    assert summary["steps_total"] == 2
    assert summary["legacy_step_count"] == 1
    assert summary["legacy_steps"][0]["resource"] == "demo:beta"
    assert summary["errors"] == []


def test_unknown_op_is_reported_as_dangling(tmp_path):
    payload = {
        "manifest": {"id": "demo"},
        "registries": {
            "cards": [
                {
                    "id": "demo:gamma",
                    "events": {"on_play": {"steps": [{"op": "definitely_not_an_op"}]}},
                }
            ]
        },
    }
    _write_package(tmp_path / "Broken.gtnmod", payload)

    summary = atom_report.build_summary(atom_report.collect(tmp_path))

    assert summary["dangling"] == ["definitely_not_an_op"]
    assert atom_report.render_text(summary)


def test_indirect_reference_detection_ignores_the_definition_line():
    corpus = [
        (ROOT / "fake_engine.py", "def _atomic_demo_atom(self):\n    return 1\n"),
        (ROOT / "fake_status.py", "STATUS_OPS = {'demo': 'demo_atom'}\n"),
    ]

    assert atom_report.find_indirect_references("demo_atom", corpus) == ["fake_status.py:1"]

    corpus_only_definition = [
        (ROOT / "fake_engine.py", "def _atomic_other_atom(self):\n    return 1\n"),
    ]
    assert atom_report.find_indirect_references("other_atom", corpus_only_definition) == []


def test_unreferenced_atoms_split_into_indirect_and_orphan():
    summary = atom_report.build_summary(atom_report.collect(ROOT / "mods"))

    indirect = {item["op"] for item in summary["indirect"]}
    orphan = set(summary["orphan"])
    # Round 20 起"未登记原子"清零：`_CORE_LOGIC_OPS` 已覆盖全部引擎 `_atomic_*`
    # （docs/引擎原子与数据步骤清单.md §21）。因此正常状态下三者都为空；
    # 一旦又有新的 `_atomic_*` 没顺手登记，下面的分支仍要求它被正确再分类——
    # 这条测试是那套再分类逻辑的回归护栏，而不是"必须存在未登记原子"的断言。
    assert indirect <= set(summary["unreferenced"])
    assert orphan <= set(summary["unreferenced"])
    assert not (indirect & set(summary["orphan"]))
    assert orphan | indirect == set(summary["unreferenced"])
    assert len(orphan) + len(indirect) == len(summary["unreferenced"])
    assert len(summary["unreferenced"]) <= summary["unregistered_atoms"]
    if summary["unregistered_atoms"] == 0:
        assert indirect == set() and orphan == set()


def test_shipped_card_data_never_calls_an_unknown_op():
    """官方包里的每个 op 都必须是运行时白名单里的 op，否则线上会直接报错。"""

    summary = atom_report.build_summary(atom_report.collect(ROOT / "mods"))

    assert summary["errors"] == []
    assert summary["steps_total"] > 0
    assert summary["dangling"] == []
