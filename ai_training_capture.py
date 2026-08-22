from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
import threading
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


_IMPORT_LOCK = threading.Lock()
_CAPTURE_BUILDER = None
_CAPTURE_IMPORT_ERROR = ""
_CAPTURE_IMPORT_ATTEMPTED = False


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return bool(default)
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return int(default)


CAPTURE_ENABLED = _env_bool("GTN_AI_HUMAN_CAPTURE_ENABLED", True)
CAPTURE_MATCH_RATE = min(1.0, max(0.0, _env_float("GTN_AI_HUMAN_CAPTURE_RATE", 1.0)))
CAPTURE_MAX_DECISIONS = max(1, _env_int("GTN_AI_HUMAN_CAPTURE_MAX_DECISIONS", 1500))
CAPTURE_HISTORY_LIMIT = max(1, _env_int("GTN_AI_HUMAN_HISTORY_LIMIT", 128))


def room_is_capture_eligible(room: Any) -> bool:
    """Return whether a room is an ordinary official human formal 1v1."""

    if not CAPTURE_ENABLED or room is None:
        return False
    if str(getattr(room, "mode", "")) != "1v1":
        return False
    if bool(getattr(room, "ai_match", False)) or bool(getattr(room, "beta_mode", False)):
        return False
    profile = dict(getattr(room, "match_mod_profile", {}) or {})
    if str(profile.get("mod_source") or "official") != "official":
        return False
    if profile.get("community_mods") or profile.get("entertainment_mods"):
        return False
    return _room_selected_for_capture(room)


def capture_decision(
    room: Any,
    actor: int,
    action_kind: str,
    payload: dict[str, Any] | None = None,
    *,
    enabled_mods: Iterable[str] | None = None,
    game_root: str | Path | None = None,
) -> dict[str, Any] | None:
    """Build an anonymous pre-action training snapshot, failing open.

    The returned object is safe to embed in a replay action. No model worker is
    started, and a capture failure never rejects or delays the player's action
    beyond the local observation-building attempt.
    """

    if not room_is_capture_eligible(room):
        return None
    stats = _room_stats(room)
    # Bound all adapter work, including malformed or no-longer-legal actions.
    # Otherwise a client could repeatedly trigger failed capture attempts after
    # the normal socket validation path and turn this optional dataset into CPU
    # amplification.
    if stats["attempted"] >= CAPTURE_MAX_DECISIONS:
        stats["skipped_limit"] += 1
        return None
    stats["attempted"] += 1
    try:
        builder = _load_capture_builder(game_root)
        raw_action = {
            "kind": str(action_kind or ""),
            "payload": _json_safe(dict(payload or {})),
        }
        snapshot = builder(
            room.engine,
            int(actor),
            raw_action,
            game_root=Path(game_root or Path(__file__).resolve().parent),
            enabled_mods=list(enabled_mods or ()),
            public_history=list(getattr(room, "_ai_training_public_history", []) or []),
            seed=0,
        )
        snapshot = _json_safe(snapshot)
        if not isinstance(snapshot, dict):
            raise TypeError("capture builder returned a non-object")
        stats["captured"] += 1
        return snapshot
    except Exception as exc:
        reason = type(exc).__name__
        stats["failed"] += 1
        stats["failure_reasons"][reason] += 1
        stats["last_error"] = f"{reason}: {str(exc)[:180]}"
        return None


def append_public_history(
    room: Any,
    actor: int,
    action_kind: str,
    payload: dict[str, Any] | None = None,
    *,
    ai_decision: dict[str, Any] | None = None,
) -> None:
    """Append one anonymous, public post-action event for later observations."""

    try:
        if not room_is_capture_eligible(room) or int(actor) not in (0, 1):
            return
        aliases = {"response": "respond", "use_equipment": "use_trigger"}
        kind = aliases.get(str(action_kind or ""), str(action_kind or ""))
        if kind not in {
            "play_card",
            "respond",
            "resolve_choice",
            "v2_ui_response",
            "use_trigger",
            "end_turn",
        }:
            return
        raw_payload = dict(payload or {})
        selected = (
            ai_decision.get("selected_action")
            if isinstance(ai_decision, dict)
            and isinstance(ai_decision.get("selected_action"), dict)
            else {}
        )
        canonical_payload = (
            selected.get("payload")
            if isinstance(selected.get("payload"), dict)
            else {}
        )
        event: dict[str, Any] = {
            "round": int(getattr(getattr(room, "engine", None), "round_num", 0) or 0),
            "player": int(actor),
            "kind": kind,
        }
        if kind == "play_card":
            event["card_def_id"] = str(raw_payload.get("def_id") or "")
            target = (
                _target_player(canonical_payload)
                if canonical_payload
                else _target_player(raw_payload)
            )
            if target is not None:
                event["target_player"] = target
        elif kind == "respond":
            event["passed"] = not bool(raw_payload.get("card_instance_id"))
            if raw_payload.get("def_id"):
                event["card_def_id"] = str(raw_payload["def_id"])
        elif kind == "use_trigger":
            event["equipment_def_id"] = str(raw_payload.get("def_id") or "")
            target = (
                _target_player(canonical_payload)
                if canonical_payload
                else _target_player(raw_payload)
            )
            if target is not None:
                event["target_player"] = target
        elif kind in {"resolve_choice", "v2_ui_response"}:
            event["choice_type"] = str(raw_payload.get("choice_type") or "resolved")
        history = getattr(room, "_ai_training_public_history", None)
        if not isinstance(history, list):
            history = []
            room._ai_training_public_history = history
        history.append(_json_safe(event))
        if len(history) > CAPTURE_HISTORY_LIMIT:
            del history[:-CAPTURE_HISTORY_LIMIT]
    except Exception:
        return


def room_capture_summary(room: Any) -> dict[str, Any]:
    stats = getattr(room, "_ai_training_capture_stats", None)
    selected = bool(getattr(room, "_ai_training_capture_selected", False))
    if not isinstance(stats, dict):
        return {
            "enabled": bool(CAPTURE_ENABLED),
            "selected": selected,
            "attempted": 0,
            "captured": 0,
            "failed": 0,
            "skipped_limit": 0,
            "failure_reasons": {},
        }
    return {
        "enabled": bool(CAPTURE_ENABLED),
        "selected": selected,
        "attempted": int(stats.get("attempted", 0) or 0),
        "captured": int(stats.get("captured", 0) or 0),
        "failed": int(stats.get("failed", 0) or 0),
        "skipped_limit": int(stats.get("skipped_limit", 0) or 0),
        "failure_reasons": dict(sorted((stats.get("failure_reasons") or {}).items())),
    }


def capture_import_error() -> str:
    return _CAPTURE_IMPORT_ERROR


def _room_selected_for_capture(room: Any) -> bool:
    cached = getattr(room, "_ai_training_capture_selected", None)
    if cached is not None:
        return bool(cached)
    if CAPTURE_MATCH_RATE >= 1.0:
        selected = True
    elif CAPTURE_MATCH_RATE <= 0.0:
        selected = False
    else:
        material = "|".join((
            str(getattr(room, "room_id", "")),
            str(getattr(room, "match_seq", "")),
            str(getattr(room, "created_at", "")),
            str((getattr(room, "match_mod_profile", {}) or {}).get("loadout_hash", "")),
        ))
        value = int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big")
        selected = value / float(1 << 64) < CAPTURE_MATCH_RATE
    room._ai_training_capture_selected = bool(selected)
    return bool(selected)


def _room_stats(room: Any) -> dict[str, Any]:
    stats = getattr(room, "_ai_training_capture_stats", None)
    if not isinstance(stats, dict):
        stats = {
            "attempted": 0,
            "captured": 0,
            "failed": 0,
            "skipped_limit": 0,
            "failure_reasons": Counter(),
            "last_error": "",
        }
        room._ai_training_capture_stats = stats
    return stats


def _load_capture_builder(game_root: str | Path | None):
    global _CAPTURE_BUILDER, _CAPTURE_IMPORT_ATTEMPTED, _CAPTURE_IMPORT_ERROR
    if _CAPTURE_BUILDER is not None:
        return _CAPTURE_BUILDER
    if _CAPTURE_IMPORT_ATTEMPTED and _CAPTURE_IMPORT_ERROR:
        raise ImportError(_CAPTURE_IMPORT_ERROR)
    with _IMPORT_LOCK:
        if _CAPTURE_BUILDER is not None:
            return _CAPTURE_BUILDER
        if _CAPTURE_IMPORT_ATTEMPTED and _CAPTURE_IMPORT_ERROR:
            raise ImportError(_CAPTURE_IMPORT_ERROR)
        _CAPTURE_IMPORT_ATTEMPTED = True
        root = Path(game_root or Path(__file__).resolve().parent).resolve()
        configured = os.environ.get("GTN_AI_ROOT")
        ai_root = Path(configured).resolve() if configured else (root.parent / "GTN-AI").resolve()
        module_path = ai_root / "gtn_ai" / "external_capture.py"
        if not module_path.is_file():
            _CAPTURE_IMPORT_ERROR = f"GTN-AI capture module not found: {module_path}"
            raise ImportError(_CAPTURE_IMPORT_ERROR)
        ai_root_text = str(ai_root)
        if ai_root_text not in sys.path:
            sys.path.insert(0, ai_root_text)
        try:
            module = importlib.import_module("gtn_ai.external_capture")
            _CAPTURE_BUILDER = module.build_external_decision_snapshot
            _CAPTURE_IMPORT_ERROR = ""
            return _CAPTURE_BUILDER
        except Exception as exc:
            _CAPTURE_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
            raise


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def _target_player(payload: dict[str, Any]) -> int | None:
    choice = payload.get("choice") if isinstance(payload.get("choice"), dict) else payload
    for key in ("target_player_id", "target_player", "target_id"):
        try:
            value = choice.get(key)
            if value is not None and int(value) in (0, 1):
                return int(value)
        except (TypeError, ValueError):
            continue
    return None
