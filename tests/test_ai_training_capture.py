from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import ai_training_capture as capture
import app as gtn


def _room(*, mode="1v1", profile=None, beta=False, ai_match=False):
    return SimpleNamespace(
        room_id=701,
        created_at=1234.5,
        mode=mode,
        beta_mode=beta,
        ai_match=ai_match,
        match_mod_profile=profile or {
            "mod_source": "official",
            "disabled_mods": [],
            "community_mods": [],
            "entertainment_mods": [],
            "loadout_hash": "official-loadout",
        },
        engine=object(),
    )


def test_capture_is_limited_to_ordinary_official_formal_1v1(monkeypatch):
    monkeypatch.setattr(capture, "CAPTURE_ENABLED", True)
    monkeypatch.setattr(capture, "CAPTURE_MATCH_RATE", 1.0)

    assert capture.room_is_capture_eligible(_room())
    assert not capture.room_is_capture_eligible(_room(mode="2v2"))
    assert not capture.room_is_capture_eligible(_room(beta=True))
    assert not capture.room_is_capture_eligible(_room(ai_match=True))
    assert not capture.room_is_capture_eligible(_room(profile={"mod_source": "community"}))
    assert not capture.room_is_capture_eligible(_room(profile={
        "mod_source": "official",
        "entertainment_mods": ["some-dlc"],
    }))


def test_capture_embeds_only_builder_output_and_updates_counts(monkeypatch, tmp_path):
    room = _room()
    expected = {
        "capture_schema_version": 1,
        "observation": {"schema_version": 3, "seat": 0},
        "legal_actions": [{"schema_version": 3, "kind": "end_turn", "payload": {}}],
        "selected_action": {"schema_version": 3, "kind": "end_turn", "payload": {}},
    }
    calls = []

    def builder(engine, actor, raw_action, **kwargs):
        calls.append((engine, actor, raw_action, kwargs))
        return expected

    monkeypatch.setattr(capture, "CAPTURE_ENABLED", True)
    monkeypatch.setattr(capture, "CAPTURE_MATCH_RATE", 1.0)
    monkeypatch.setattr(capture, "_CAPTURE_BUILDER", builder)

    result = capture.capture_decision(
        room,
        0,
        "end_turn",
        {},
        enabled_mods=["Classic.json"],
        game_root=tmp_path,
    )

    assert result == expected
    assert calls[0][0] is room.engine
    assert calls[0][1] == 0
    assert calls[0][2] == {"kind": "end_turn", "payload": {}}
    assert calls[0][3]["enabled_mods"] == ["Classic.json"]
    assert calls[0][3]["public_history"] == []
    assert capture.room_capture_summary(room) == {
        "enabled": True,
        "selected": True,
        "attempted": 1,
        "captured": 1,
        "failed": 0,
        "skipped_limit": 0,
        "failure_reasons": {},
    }


def test_capture_failure_is_fail_open_and_rate_limited_by_match(monkeypatch, tmp_path):
    room = _room()

    def broken_builder(*_args, **_kwargs):
        raise ValueError("not canonical")

    monkeypatch.setattr(capture, "CAPTURE_ENABLED", True)
    monkeypatch.setattr(capture, "CAPTURE_MATCH_RATE", 1.0)
    monkeypatch.setattr(capture, "CAPTURE_MAX_DECISIONS", 1)
    monkeypatch.setattr(capture, "_CAPTURE_BUILDER", broken_builder)

    assert capture.capture_decision(room, 0, "unknown", {}, game_root=tmp_path) is None
    assert capture.capture_decision(room, 0, "unknown", {}, game_root=tmp_path) is None
    summary = capture.room_capture_summary(room)
    assert summary["attempted"] == 1
    assert summary["captured"] == 0
    assert summary["failed"] == 1
    assert summary["skipped_limit"] == 1
    assert summary["failure_reasons"] == {"ValueError": 1}


def test_capture_builder_import_failure_is_cached_for_the_process(monkeypatch):
    room = _room()
    imports = []

    def broken_import(name):
        imports.append(name)
        raise RuntimeError("broken runtime bundle")

    monkeypatch.setattr(capture, "CAPTURE_ENABLED", True)
    monkeypatch.setattr(capture, "CAPTURE_MATCH_RATE", 1.0)
    monkeypatch.setattr(capture, "_CAPTURE_BUILDER", None)
    monkeypatch.setattr(capture, "_CAPTURE_IMPORT_ATTEMPTED", False)
    monkeypatch.setattr(capture, "_CAPTURE_IMPORT_ERROR", "")
    monkeypatch.setattr(capture.importlib, "import_module", broken_import)
    game_root = Path(__file__).resolve().parents[1]

    assert capture.capture_decision(room, 0, "end_turn", {}, game_root=game_root) is None
    assert capture.capture_decision(room, 0, "end_turn", {}, game_root=game_root) is None

    assert imports == ["gtn_ai.external_capture"]


def test_replay_action_keeps_decision_snapshot_outside_public_action_payload():
    room = SimpleNamespace(
        room_id=702,
        created_at=gtn.time.time(),
        engine=SimpleNamespace(phase="action", round_num=1, current_player=0),
        _history_recorded=False,
        _replay_actions=[],
    )
    decision = {
        "observation": {"schema_version": 3, "seat": 0},
        "legal_actions": [{"schema_version": 3, "kind": "end_turn", "payload": {}}],
        "selected_action": {"schema_version": 3, "kind": "end_turn", "payload": {}},
    }
    with (
        mock.patch.object(gtn, "ensure_room_replay_keyframe"),
        mock.patch.object(gtn, "_replay_capture_budgeted_state", return_value={"ok": True}),
    ):
        gtn.record_room_replay_action(
            room,
            "end_turn",
            0,
            {"auto": False},
            ai_decision=decision,
        )

    recorded = room._replay_actions[0]
    assert recorded["payload"] == {"auto": False}
    assert recorded["ai_decision"] == decision
    assert "ai_decision" not in recorded["payload"]


def test_replay_reset_starts_a_fresh_match_capture_budget():
    room = _room()
    room._ai_training_capture_selected = True
    room._ai_training_capture_stats = {"captured": 12}
    room._ai_training_enabled_mod_filenames = ("Classic.json",)
    room._ai_training_public_history = [{"kind": "end_turn"}]

    gtn.reset_room_replay(room)

    assert not hasattr(room, "_ai_training_capture_selected")
    assert not hasattr(room, "_ai_training_capture_stats")
    assert not hasattr(room, "_ai_training_enabled_mod_filenames")
    assert not hasattr(room, "_ai_training_public_history")


def test_successful_replay_actions_feed_anonymous_public_history(monkeypatch):
    room = _room()
    room.engine = SimpleNamespace(round_num=3)
    monkeypatch.setattr(capture, "CAPTURE_ENABLED", True)
    monkeypatch.setattr(capture, "CAPTURE_MATCH_RATE", 1.0)

    capture.append_public_history(
        room,
        0,
        "play_card",
        {
            "def_id": "vanilla:light",
            "target_player_id": 1,
            "from_name": "must-not-leak",
        },
    )

    assert room._ai_training_public_history == [{
        "round": 3,
        "player": 0,
        "kind": "play_card",
        "card_def_id": "vanilla:light",
        "target_player": 1,
    }]
