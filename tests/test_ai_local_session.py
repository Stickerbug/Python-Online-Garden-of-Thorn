from __future__ import annotations

from pathlib import Path
from unittest import mock

import app as gtn


class _EndTurnWorker:
    def decide_and_execute(self, engine, **kwargs):
        # A bridge replacement is not required to preserve app-only markers.
        # The caller must restore Phelren's stable engine-local isolation flag.
        if hasattr(engine, "_solo_history_disabled"):
            delattr(engine, "_solo_history_disabled")
        actor = int(kwargs["player_id"])
        result = engine.end_turn(actor)
        assert result.get("success")
        return engine, {
            "action": {"kind": "end_turn", "payload": {}},
            "decision_id": 7,
            "elapsed_ms": 1.5,
        }


class _StartOnlyWorker:
    def start(self):
        return None


def _test_engine():
    deck = ["Light"] * gtn.DECK_SIZE
    return gtn.create_solo_engine(
        deck,
        deck,
        event0=1,
        event1=1,
        player_names=["Garden AI", "Human"],
    )


def test_ai_turn_executes_atomically_then_returns_control_to_human():
    sid = "ai-local-turn-test"
    engine = _test_engine()
    meta = {
        "session_id": "ai-local-turn-session",
        "seed": 10,
        "human_player_id": 1,
        "ai_player_id": 0,
        "enabled_mods": [],
        "action_index": 0,
        "thinking": True,
        "diagnostic_metadata": {},
    }
    gtn.solo_sessions[sid] = engine
    gtn.ai_test_sessions[sid] = meta
    meta["replay_room"] = gtn._create_ai_test_replay_room(sid, engine, meta)
    action_lock = gtn._solo_action_lock_for_sid(sid)

    def assert_human_state_is_emitted_after_unlock(*_args, **_kwargs):
        acquired = action_lock.acquire(blocking=False)
        assert acquired, "human turn was emitted while the AI still held the action lock"
        action_lock.release()

    try:
        with (
            mock.patch.object(gtn, "get_local_ai_worker", return_value=_EndTurnWorker()),
            mock.patch.object(gtn, "send_solo_state"),
            mock.patch.object(
                gtn,
                "send_solo_state_with_pending",
                side_effect=assert_human_state_is_emitted_after_unlock,
            ),
            mock.patch.object(gtn.socketio, "sleep"),
        ):
            gtn._run_ai_test_turn(sid)

        assert engine.current_player == 1
        assert meta["thinking"] is False
        assert meta["action_index"] == 1
        assert meta["latest_decision_id"] == 7
        assert meta["latest_ai_decision_id"] == 7
        assert meta["recent_ai_decisions"][0]["kind"] == "end_turn"
        assert meta["last_ai_action"]["kind"] == "end_turn"
        assert engine._solo_history_disabled is True
        assert meta["replay_room"]._replay_actions[-1]["type"] == "end_turn"
        assert meta["replay_room"]._replay_actions[-1]["actor"] == 0
    finally:
        gtn.solo_sessions.pop(sid, None)
        gtn.ai_test_sessions.pop(sid, None)
        gtn._SOLO_ACTION_LOCKS.pop(sid, None)


def test_ai_turn_waits_for_the_scheduling_human_action_to_unlock():
    sid = "ai-local-lock-handoff-test"
    engine = _test_engine()
    meta = {
        "session_id": "ai-local-lock-handoff-session",
        "seed": 12,
        "human_player_id": 1,
        "ai_player_id": 0,
        "enabled_mods": [],
        "action_index": 0,
        "thinking": True,
        "diagnostic_metadata": {},
    }
    gtn.solo_sessions[sid] = engine
    gtn.ai_test_sessions[sid] = meta
    meta["replay_room"] = gtn._create_ai_test_replay_room(sid, engine, meta)
    action_lock = gtn._solo_action_lock_for_sid(sid)
    assert action_lock.acquire(blocking=False)
    released = False

    def release_scheduling_action(_seconds):
        nonlocal released
        if not released:
            released = True
            action_lock.release()

    try:
        with (
            mock.patch.object(gtn, "get_local_ai_worker", return_value=_EndTurnWorker()),
            mock.patch.object(gtn, "send_solo_state"),
            mock.patch.object(gtn, "send_solo_state_with_pending"),
            mock.patch.object(gtn.socketio, "sleep", side_effect=release_scheduling_action),
        ):
            gtn._run_ai_test_turn(sid)

        assert released is True
        assert engine.current_player == 1
        assert meta["action_index"] == 1
        assert meta["thinking"] is False
    finally:
        if not released:
            action_lock.release()
        gtn.solo_sessions.pop(sid, None)
        gtn.ai_test_sessions.pop(sid, None)
        gtn._SOLO_ACTION_LOCKS.pop(sid, None)


def test_ai_visible_delays_and_recent_decision_summary_use_the_requested_ranges():
    engine = _test_engine()
    card_action = {
        "kind": "play_card",
        "payload": {"hand_slot": 0, "choice": {"target_player_id": 1}},
    }
    summary = gtn._ai_test_decision_summary(engine, 0, card_action, 12, 4)

    assert summary["decision_id"] == 12
    assert summary["card_def_id"] == engine.players[0].hand[0].def_id
    assert summary["target_relation"] == "opponent"

    meta = {}
    for decision_id in range(gtn.AI_TEST_RECENT_DECISION_LIMIT + 2):
        gtn._remember_ai_test_decision(meta, {**summary, "decision_id": decision_id})
    assert len(meta["recent_ai_decisions"]) == gtn.AI_TEST_RECENT_DECISION_LIMIT
    assert meta["latest_ai_decision_id"] == gtn.AI_TEST_RECENT_DECISION_LIMIT + 1

    with mock.patch.object(gtn.random, "uniform", side_effect=[1.4, 2.7, 1.6]) as uniform:
        assert gtn._ai_test_visible_action_delay(card_action) == 1.4
        assert gtn._ai_test_pregame_delay("opening_event") == 2.7
        assert gtn._ai_test_pregame_delay("draft_pick") == 1.6
    assert uniform.call_args_list == [
        mock.call(gtn.AI_TEST_CARD_DELAY_MIN_SECONDS, gtn.AI_TEST_CARD_DELAY_MAX_SECONDS),
        mock.call(gtn.AI_TEST_PREGAME_DELAY_MIN_SECONDS, gtn.AI_TEST_PREGAME_DELAY_MAX_SECONDS),
        mock.call(gtn.AI_TEST_CARD_DELAY_MIN_SECONDS, gtn.AI_TEST_CARD_DELAY_MAX_SECONDS),
    ]


def test_ai_session_uses_formal_room_presence_with_solo_state_protocol():
    source = open(gtn.__file__, encoding="utf-8").read()
    assert "players[sid]['status'] = 'in_game'" in source
    assert "players[sid]['status'] = 'ai_test'" not in source
    assert "_env_int('GTN_AI_1V1_MAX_ACTIVE', 5)" in source
    assert "os.environ.get('GTN_AI_1V1_TEST_ENABLED', '1')" in source
    assert "os.environ.get('GTN_AI_PUBLIC_ENTRY_ENABLED', '0')" in source


def test_ai_response_windows_keep_the_human_perspective():
    sid = "ai-response-perspective-test"
    try:
        gtn.ai_test_sessions[sid] = {
            "human_player_id": 0,
            "ai_player_id": 1,
        }
        assert gtn._solo_response_view_perspective(sid, 1) == 0

        gtn.ai_test_sessions[sid]["human_player_id"] = 1
        assert gtn._solo_response_view_perspective(sid, 0) == 1
    finally:
        gtn.ai_test_sessions.pop(sid, None)

    assert gtn._solo_response_view_perspective(sid, 1) == 1


def test_ai_room_rejects_parallel_formal_combat_protocol():
    sid = "ai-formal-protocol-reject-test"
    engine = _test_engine()
    gtn.players[sid] = {
        "nickname": "Protocol Human",
        "status": "in_game",
        "room_id": 123,
    }
    gtn.solo_sessions[sid] = engine
    gtn.ai_test_sessions[sid] = {
        "session_id": "protocol-reject-session",
        "human_player_id": 1,
        "ai_player_id": 0,
    }
    try:
        with (
            mock.patch.object(gtn, "request", mock.Mock(sid=sid)),
            mock.patch.object(gtn, "_socket_rate_allowed", return_value=True),
            mock.patch.object(gtn.socketio, "emit") as emit,
            mock.patch.object(gtn, "send_solo_state_with_pending") as resync,
        ):
            assert gtn.socket_guard("play_card", {}, require_player=True) is None

        payload = emit.call_args.args[1]
        assert emit.call_args.args[0] == "action_rejected"
        assert payload["code"] == "STATE_VERSION_OLD"
        resync.assert_called_once_with(sid)
    finally:
        gtn.solo_sessions.pop(sid, None)
        gtn.ai_test_sessions.pop(sid, None)
        gtn.players.pop(sid, None)


def test_ai_match_finalizer_saves_a_private_phelren_replay_without_rank_stats():
    sid = "ai-replay-finalizer-test"
    engine = _test_engine()
    assert engine.surrender(0).get("success")
    meta = {
        "session_id": "ai-replay-finalizer-session",
        "created_at_ts": gtn.time.time() - 12,
        "human_player_id": 1,
        "ai_player_id": 0,
        "human_name": "Replay Human",
        "ai_name": "Phelren",
        "policy_label": "Phelren V1",
        "diagnostic_metadata": {},
    }
    gtn.players[sid] = {
        "nickname": "Replay Human",
        "user_id": 4242,
        "is_registered_user": True,
        "disabled_mods": [],
        "skin": {},
        "beta_mode": False,
        "mode": "1v1",
        "mod_source": "official",
    }
    gtn.solo_sessions[sid] = engine
    gtn.ai_test_sessions[sid] = meta
    meta["replay_room"] = gtn._create_ai_test_replay_room(sid, engine, meta)

    try:
        with (
            mock.patch.object(gtn, "DB_AVAILABLE", True),
            mock.patch.object(gtn, "save_match_summary", return_value=71) as save_match,
            mock.patch.object(gtn, "save_replay_snapshot", return_value=81) as save_replay,
        ):
            summary = gtn._finalize_ai_test_replay(sid, engine, meta)

        assert summary["replay_prefix"] == "P"
        assert summary["replay_ref"] == "P-81"
        assert summary["player_ids"] == [None, 4242]
        assert summary["valid_for_ranking"] is False
        assert summary["ranking_invalid_reason"] == "phelren_ai_match"
        assert meta["replay_saved"] is True
        assert save_match.call_count == 1
        replay_payload = save_replay.call_args.args[1]
        assert replay_payload["replay_prefix"] == "P"
        assert replay_payload["replay"]["actions"][-1]["type"] == "game_over"
    finally:
        gtn.solo_sessions.pop(sid, None)
        gtn.ai_test_sessions.pop(sid, None)
        gtn.players.pop(sid, None)


def test_replay_api_accepts_phelren_prefixed_references():
    client = gtn.app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 4242
        session["username"] = "Replay Human"
    replay_item = {
        "id": 81,
        "replay_prefix": "P",
        "replay_ref": "P-81",
        "players": ["Phelren", "Replay Human"],
    }
    timeline = {
        "replay": {"id": 81, "replay_prefix": "P", "replay_ref": "P-81"},
        "timeline": [],
        "total_frames": 0,
    }
    with (
        mock.patch.object(gtn, "DB_AVAILABLE", True),
        mock.patch.object(gtn, "replay_api_allowed", return_value=True),
        mock.patch.object(gtn, "get_replay", return_value=replay_item) as get_replay,
        mock.patch.object(gtn, "replay_item_visible_to_current_user", return_value=True),
        mock.patch.object(gtn, "replay_timeline", return_value=timeline) as get_timeline,
    ):
        detail_response = client.get("/api/replays/P-81")
        timeline_response = client.get("/api/replays/P-81/timeline")

    assert detail_response.status_code == 200
    assert detail_response.get_json()["replay"]["replay_ref"] == "P-81"
    assert timeline_response.status_code == 200
    assert timeline_response.get_json()["replay"]["replay_ref"] == "P-81"
    get_replay.assert_has_calls([mock.call("P-81"), mock.call("P-81")])
    get_timeline.assert_called_once_with(81, offset=None, limit=None)


def test_registered_socket_player_can_start_public_ai_match():
    http_client = gtn.app.test_client()
    with http_client.session_transaction() as session:
        session["user_id"] = 101
    client = gtn.socketio.test_client(gtn.app, flask_test_client=http_client)
    room_map = gtn.socketio.server.manager.rooms["/"][None]
    sid = next(key for key, value in room_map.items() if value == client.eio_sid)
    gtn.players[sid] = {
        "nickname": "Local Human",
        "user_id": 101,
        "is_registered_user": True,
        "status": "lobby",
        "room_id": None,
        "disabled_mods": [],
        "skin": {},
        "beta_mode": False,
        "mode": "1v1",
    }
    try:
        with (
            mock.patch.object(gtn, "GTN_AI_1V1_TEST_ENABLED", True),
            mock.patch.object(gtn, "GTN_AI_PUBLIC_ENTRY_ENABLED", True),
            mock.patch.object(gtn, "get_local_ai_worker", return_value=_StartOnlyWorker()),
            mock.patch.object(gtn.secrets, "randbelow", return_value=0),
            mock.patch.object(gtn, "_start_socket_background_task", return_value=None),
            mock.patch.object(gtn, "broadcast_lobby") as broadcast_lobby,
            mock.patch.object(
                gtn,
                "_start_ai_test_background_task",
                side_effect=gtn._start_ai_test_session,
            ),
        ):
            client.emit("ai_1v1_start", {})
            received = client.get_received()

        names = [event["name"] for event in received]
        assert names == ["ai_1v1_status", "game_phase", "event_select", "ai_1v1_status"]
        phase = next(event["args"][0] for event in received if event["name"] == "game_phase")
        state = next(event["args"][0] for event in received if event["name"] == "event_select")
        assert phase["phase"] == "event_select"
        assert phase["solo"] is True
        assert state["ai_test"] is True
        assert state["your_id"] == 0
        assert state["ai_player_id"] == 1
        assert state["player_names"] == ["Local Human", "Phelren"]
        assert state["player_avatar_kinds"] == ["", "phelren"]
        room_id = gtn.players[sid]["room_id"]
        assert isinstance(room_id, int)
        assert gtn.players[sid]["status"] == "in_game"
        assert gtn.rooms[room_id].ai_match is True
        assert gtn.rooms[room_id].ai_owner_sid == sid
        assert gtn.player_avatar_kind_for_sid(gtn.rooms[room_id].ai_sid, gtn.rooms[room_id]) == "phelren"
        assert state["room_id"] == room_id
        assert not any(player["sid"] == sid for player in gtn.get_lobby_list(False))
        ongoing = next(game for game in gtn.get_ongoing_games(False) if game["room_id"] == room_id)
        assert {ongoing["player1"], ongoing["player2"]} == {"Local Human", "Phelren"}
        assert ongoing["ai_match"] is True
        assert ongoing["match_kind"] == "phelren"
        assert ongoing["ai_policy_label"] == "Phelren V1"
        broadcast_lobby.assert_called_once_with()
        assert sid in gtn.solo_sessions
        assert sid in gtn.ai_test_sessions
    finally:
        with gtn._lock:
            gtn._drop_solo_session_locked(sid)
        gtn.players.pop(sid, None)
        client.disconnect()


def test_active_ai_match_survives_disconnect_and_rejoins_through_normal_reconnect():
    old_http = gtn.app.test_client()
    old_client = gtn.socketio.test_client(gtn.app, flask_test_client=old_http)
    room_map = gtn.socketio.server.manager.rooms["/"][None]
    old_sid = next(key for key, value in room_map.items() if value == old_client.eio_sid)
    room_id = max([int(key) for key in gtn.rooms if str(key).isdigit()] + [900000]) + 1
    engine = _test_engine()
    player = {
        "nickname": "Reconnect Human",
        "user_id": 1101,
        "account_player_id": "reconnect-human",
        "is_registered_user": True,
        "status": "in_game",
        "room_id": room_id,
        "disabled_mods": [],
        "skin": {},
        "beta_mode": False,
        "mode": "1v1",
    }
    meta = {
        "session_id": "ai-reconnect-session",
        "seed": 17,
        "human_player_id": 1,
        "ai_player_id": 0,
        "human_name": player["nickname"],
        "ai_name": "Phelren",
        "enabled_mods": [],
        "action_index": 0,
        "thinking": False,
        "timer_running": True,
        "pregame_ai_running": False,
        "diagnostic_finished": True,
        "policy_label": "Phelren V1",
        "diagnostic_metadata": {},
    }
    gtn.players[old_sid] = player
    gtn.solo_sessions[old_sid] = engine
    gtn.ai_test_sessions[old_sid] = meta
    room = gtn._create_ai_test_replay_room(old_sid, engine, meta, room_id=room_id)
    meta["replay_room"] = room
    gtn.rooms[room_id] = room

    new_client = None
    new_sid = None
    try:
        old_client.disconnect()

        assert room_id in gtn.rooms
        assert old_sid in gtn.solo_sessions
        assert old_sid in gtn.ai_test_sessions
        assert old_sid in room.disconnected_players
        assert gtn._tick_ai_test_match_timer(old_sid)["kind"] == "paused_disconnect"
        candidate, candidate_sid = gtn.find_reconnect_candidate_locked(
            nickname=player["nickname"],
            user_id=player["user_id"],
            account_player_id=player["account_player_id"],
            beta_mode=False,
        )
        assert candidate is room
        assert candidate_sid == old_sid

        new_http = gtn.app.test_client()
        new_client = gtn.socketio.test_client(gtn.app, flask_test_client=new_http)
        room_map = gtn.socketio.server.manager.rooms["/"][None]
        new_sid = next(key for key, value in room_map.items() if value == new_client.eio_sid)
        gtn.players[new_sid] = {
            **player,
            "status": "reconnecting",
            "room_id": None,
        }
        with (
            mock.patch.object(gtn, "schedule_ai_test_match_timer") as schedule_timer,
            mock.patch.object(gtn, "schedule_ai_test_pregame") as schedule_pregame,
            mock.patch.object(gtn, "schedule_ai_test_turn") as schedule_turn,
            mock.patch.object(gtn, "broadcast_lobby"),
        ):
            new_client.emit("reconnect_accept", {"room_id": room_id, "old_sid": old_sid})
            received = new_client.get_received()

        assert any(event["name"] == "solo_state" for event in received)
        assert old_sid not in gtn.solo_sessions
        assert old_sid not in gtn.ai_test_sessions
        assert gtn.solo_sessions[new_sid] is engine
        assert gtn.ai_test_sessions[new_sid] is meta
        assert room.ai_owner_sid == new_sid
        assert room.player_sids[1] == new_sid
        assert old_sid not in room.disconnected_players
        assert not getattr(room, "_phelren_reconnect_accept_pending", {})
        assert gtn.players[new_sid]["status"] == "in_game"
        assert gtn.players[new_sid]["room_id"] == room_id
        assert meta["owner_disconnected"] is False
        assert meta["timer_running"] is False
        schedule_timer.assert_called_once_with(new_sid)
        schedule_pregame.assert_called_once_with(new_sid)
        assert schedule_turn.call_count >= 1
        assert all(call.args == (new_sid,) for call in schedule_turn.call_args_list)
    finally:
        for timer in list(room.reconnect_timers.values()):
            timer.cancel()
        with gtn._lock:
            gtn._drop_solo_session_locked(new_sid or old_sid)
            if new_sid:
                gtn.players.pop(new_sid, None)
            gtn.players.pop(old_sid, None)
        if new_client is not None and new_client.is_connected():
            new_client.disconnect()


def test_ai_disconnect_timeout_waits_for_busy_action_before_cleanup():
    sid = "ai-disconnect-timeout-cleanup-test"
    room_id = max([int(key) for key in gtn.rooms if str(key).isdigit()] + [910000]) + 1
    engine = _test_engine()
    meta = {
        "session_id": "ai-disconnect-timeout-cleanup-session",
        "seed": 23,
        "human_player_id": 1,
        "ai_player_id": 0,
        "human_name": "Disconnected Human",
        "ai_name": "Phelren",
        "enabled_mods": [],
        "action_index": 0,
        "thinking": True,
        "diagnostic_finished": True,
        "policy_label": "Phelren V1",
        "diagnostic_metadata": {},
    }
    gtn.solo_sessions[sid] = engine
    gtn.ai_test_sessions[sid] = meta
    room = gtn._create_ai_test_replay_room(sid, engine, meta, room_id=room_id)
    meta["replay_room"] = room
    room.disconnected_players[sid] = {
        "player_index": 1,
        "nickname": meta["human_name"],
        "disconnect_time": gtn.time.time() - 60,
        "disconnect_attempt": 1,
        "reconnect_timeout": 30,
    }
    gtn.rooms[room_id] = room
    action_lock = gtn._solo_action_lock_for_sid(sid)
    assert action_lock.acquire(blocking=False)
    timers = []

    class DeferredTimer:
        def __init__(self, interval, callback, args=None):
            self.interval = interval
            self.callback = callback
            self.args = list(args or [])
            self.daemon = False
            self.started = False
            self.cancelled = False
            timers.append(self)

        def start(self):
            self.started = True

        def cancel(self):
            self.cancelled = True

    try:
        with (
            mock.patch.object(gtn.threading, "Timer", DeferredTimer),
            mock.patch.object(gtn, "_schedule_game_over_cleanup") as schedule_cleanup,
            mock.patch.object(gtn, "broadcast_game_state"),
            mock.patch.object(gtn, "broadcast_lobby"),
        ):
            gtn.reconnect_timeout(room_id, sid)
            assert engine.game_over is False
            schedule_cleanup.assert_not_called()
            assert len(timers) == 1
            assert timers[0].started is True
            assert room.reconnect_timers[sid] is timers[0]

            action_lock.release()
            timers[0].callback(*timers[0].args)

            assert engine.game_over is True
            assert engine.phase == "game_over"
            assert timers[0].cancelled is True
            schedule_cleanup.assert_called_once_with(room)
    finally:
        if action_lock.locked():
            action_lock.release()
        with gtn._lock:
            gtn._drop_solo_session_locked(sid)
            gtn.rooms.pop(room_id, None)


def test_ai_disconnect_timeout_yields_to_arrived_reconnect_accept():
    old_sid = "ai-reconnect-reservation-old"
    new_sid = "ai-reconnect-reservation-new"
    room_id = max([int(key) for key in gtn.rooms if str(key).isdigit()] + [915000]) + 1
    engine = _test_engine()
    meta = {
        "session_id": "ai-reconnect-reservation-session",
        "seed": 29,
        "human_player_id": 1,
        "ai_player_id": 0,
        "human_name": "Reserved Human",
        "ai_name": "Phelren",
        "enabled_mods": [],
        "action_index": 0,
        "thinking": False,
        "diagnostic_finished": True,
        "policy_label": "Phelren V1",
        "diagnostic_metadata": {},
    }
    gtn.solo_sessions[old_sid] = engine
    gtn.ai_test_sessions[old_sid] = meta
    room = gtn._create_ai_test_replay_room(old_sid, engine, meta, room_id=room_id)
    meta["replay_room"] = room
    room.disconnected_players[old_sid] = {
        "player_index": 1,
        "nickname": meta["human_name"],
        "user_id": 2201,
        "account_player_id": "reserved-human",
        "disconnect_time": gtn.time.time() - 60,
        "disconnect_attempt": 1,
        "reconnect_timeout": 30,
    }
    gtn.rooms[room_id] = room
    gtn.players[new_sid] = {
        "nickname": meta["human_name"],
        "user_id": 2201,
        "account_player_id": "reserved-human",
        "status": "reconnecting",
        "room_id": None,
        "beta_mode": False,
    }
    timers = []

    class DeferredTimer:
        def __init__(self, interval, callback, args=None):
            self.interval = interval
            self.callback = callback
            self.args = list(args or [])
            self.daemon = False
            self.started = False
            self.cancelled = False
            timers.append(self)

        def start(self):
            self.started = True

        def cancel(self):
            self.cancelled = True

    try:
        with gtn._lock:
            resolved_sid, reserved, wait_for_staging, conflict = (
                gtn._reserve_phelren_reconnect_accept_locked(
                    room_id,
                    old_sid,
                    new_sid,
                    gtn._PHELREN_RECONNECT_ACCEPT_WAIT_SECONDS,
                )
            )
        assert resolved_sid == old_sid
        assert reserved is True
        assert wait_for_staging is False
        assert conflict is False

        with (
            mock.patch.object(gtn.threading, "Timer", DeferredTimer),
            mock.patch.object(gtn, "_schedule_game_over_cleanup") as schedule_cleanup,
            mock.patch.object(gtn, "broadcast_game_state"),
            mock.patch.object(gtn, "broadcast_lobby"),
        ):
            # This simulates the timeout callback winning the lock immediately
            # after the previous mutation clears. The already-arrived accept
            # reservation must still win and keep the engine active.
            gtn.reconnect_timeout(room_id, old_sid)
            assert engine.game_over is False
            schedule_cleanup.assert_not_called()
            assert len(timers) == 1
            assert timers[0].started is True
            assert room.reconnect_timers[old_sid] is timers[0]

            with gtn._lock:
                gtn._release_phelren_reconnect_accept_reservation_locked(
                    room,
                    old_sid,
                    new_sid,
                )
            timers[0].callback(*timers[0].args)

            assert engine.game_over is True
            assert engine.phase == "game_over"
            assert timers[0].cancelled is True
            schedule_cleanup.assert_called_once_with(room)
    finally:
        with gtn._lock:
            gtn._drop_solo_session_locked(old_sid)
            gtn.rooms.pop(room_id, None)
            gtn.players.pop(new_sid, None)


def test_ai_game_over_cleanup_is_idempotent_and_removes_session():
    sid = "ai-game-over-cleanup-test"
    room_id = max([int(key) for key in gtn.rooms if str(key).isdigit()] + [920000]) + 1
    engine = _test_engine()
    engine.game_over = True
    engine.phase = "game_over"
    meta = {
        "session_id": "ai-game-over-cleanup-session",
        "human_player_id": 1,
        "ai_player_id": 0,
        "diagnostic_finished": True,
    }
    gtn.solo_sessions[sid] = engine
    gtn.ai_test_sessions[sid] = meta
    room = gtn._create_ai_test_replay_room(sid, engine, meta, room_id=room_id)
    meta["replay_room"] = room
    gtn.rooms[room_id] = room
    timers = []

    class DeferredTimer:
        def __init__(self, interval, callback):
            self.interval = interval
            self.callback = callback
            self.daemon = False
            self.started = False
            self.cancelled = False
            timers.append(self)

        def start(self):
            self.started = True

        def cancel(self):
            self.cancelled = True

    try:
        with (
            mock.patch.object(gtn.threading, "Timer", DeferredTimer),
            mock.patch.object(gtn, "broadcast_lobby") as broadcast_lobby,
        ):
            assert gtn._schedule_game_over_cleanup(room) is True
            assert gtn._schedule_game_over_cleanup(room) is False
            assert len(timers) == 2
            assert timers[0].started is True
            assert timers[1].started is False
            timers[0].callback()

        assert room_id not in gtn.rooms
        assert sid not in gtn.solo_sessions
        assert sid not in gtn.ai_test_sessions
        assert timers[0].cancelled is True
        broadcast_lobby.assert_called_once_with()
    finally:
        with gtn._lock:
            gtn._drop_solo_session_locked(sid)
            gtn.rooms.pop(room_id, None)


def test_ai_game_over_cleanup_retries_until_native_guard_clears():
    sid = "ai-game-over-cleanup-guard-test"
    room_id = max([int(key) for key in gtn.rooms if str(key).isdigit()] + [925000]) + 1
    engine = _test_engine()
    engine.game_over = True
    engine.phase = "game_over"
    meta = {
        "session_id": "ai-game-over-cleanup-guard-session",
        "human_player_id": 1,
        "ai_player_id": 0,
        "diagnostic_finished": True,
    }
    completion = gtn._new_phelren_call_completion()
    meta["_phelren_native_completion"] = completion
    gtn.solo_sessions[sid] = engine
    gtn.ai_test_sessions[sid] = meta
    room = gtn._create_ai_test_replay_room(sid, engine, meta, room_id=room_id)
    meta["replay_room"] = room
    gtn.rooms[room_id] = room
    timers = []

    class DeferredTimer:
        def __init__(self, interval, callback):
            self.interval = interval
            self.callback = callback
            self.daemon = False
            self.started = False
            self.cancelled = False
            timers.append(self)

        def start(self):
            self.started = True

        def cancel(self):
            self.cancelled = True

    try:
        with (
            mock.patch.object(gtn.threading, "Timer", DeferredTimer),
            mock.patch.object(gtn, "broadcast_lobby") as broadcast_lobby,
        ):
            assert gtn._schedule_game_over_cleanup(room) is True
            timers[0].callback()

            assert room_id in gtn.rooms
            assert sid in gtn.ai_test_sessions
            assert room._game_over_cleanup_timer is timers[0]
            assert len(timers) == 2
            assert timers[1].interval == 0.25
            assert timers[1].started is True
            broadcast_lobby.assert_not_called()

            meta.pop("_phelren_native_completion", None)
            timers[1].callback()

        assert room_id not in gtn.rooms
        assert sid not in gtn.solo_sessions
        assert sid not in gtn.ai_test_sessions
        broadcast_lobby.assert_called_once_with()
    finally:
        with gtn._lock:
            gtn._drop_solo_session_locked(sid)
            gtn.rooms.pop(room_id, None)


def test_ai_match_client_route_participates_in_network_recovery():
    source = (Path(gtn.__file__).parent / "static" / "js" / "game.js").read_text(encoding="utf-8")
    assert "const isAiMatch = !!(payload && (payload.ai_test || payload.ai_match));" in source
    assert "(soloMode && !isAiMatch)" in source
    assert "if (data && data.ai_test) rememberActiveMatchRoute(data, 'solo_state');" in source


def test_live_ai_room_can_be_spectated_and_closes_spectators_with_owner():
    owner_http = gtn.app.test_client()
    spectator_http = gtn.app.test_client()
    owner_client = gtn.socketio.test_client(gtn.app, flask_test_client=owner_http)
    spectator_client = gtn.socketio.test_client(gtn.app, flask_test_client=spectator_http)
    room_map = gtn.socketio.server.manager.rooms["/"][None]
    owner_sid = next(key for key, value in room_map.items() if value == owner_client.eio_sid)
    spectator_sid = next(key for key, value in room_map.items() if value == spectator_client.eio_sid)
    room_id = 900_000_000
    while room_id in gtn.rooms:
        room_id += 1
    engine = _test_engine()
    engine.player_names = ["Phelren", "Spectated Human"]
    meta = {
        "session_id": "ai-live-spectate-session",
        "created_at_ts": gtn.time.time(),
        "human_player_id": 1,
        "ai_player_id": 0,
        "human_name": "Spectated Human",
        "ai_name": "Phelren",
        "policy_label": "Phelren V1",
        "diagnostic_finished": True,
    }
    gtn.players[owner_sid] = {
        "nickname": "Spectated Human",
        "user_id": 201,
        "is_registered_user": True,
        "allow_guest_spectators": True,
        "status": "in_game",
        "room_id": room_id,
        "spectating_room": None,
        "disabled_mods": [],
        "skin": {},
        "beta_mode": False,
        "mode": "1v1",
    }
    gtn.players[spectator_sid] = {
        "nickname": "Watching Human",
        "user_id": 202,
        "is_registered_user": True,
        "status": "lobby",
        "room_id": None,
        "spectating_room": None,
        "disabled_mods": [],
        "skin": {},
        "beta_mode": False,
        "mode": "1v1",
    }
    room = gtn._create_ai_test_replay_room(owner_sid, engine, meta, room_id=room_id)
    meta["replay_room"] = room
    gtn.solo_sessions[owner_sid] = engine
    gtn.ai_test_sessions[owner_sid] = meta
    gtn.rooms[room_id] = room

    try:
        owner_client.get_received()
        spectator_client.get_received()
        original_phase = engine.phase
        engine.phase = "draft"
        meta["_phelren_native_completion"] = gtn._new_phelren_call_completion()
        with mock.patch.object(gtn, "broadcast_game_state") as deferred_broadcast:
            spectator_client.emit("spectate", {"room_id": room_id})
            guarded_received = spectator_client.get_received()
        assert not any(event["name"] == "spectate_enter" for event in guarded_received)
        assert any(
            event["name"] == "server_error"
            and event["args"][0].get("code") == "ACTION_BUSY"
            for event in guarded_received
        )
        assert gtn.players[spectator_sid]["status"] == "lobby"
        assert gtn.players[spectator_sid]["spectating_room"] is None
        assert spectator_sid not in room.spectators
        deferred_broadcast.assert_called_once_with(room)
        meta.pop("_phelren_native_completion", None)
        engine.phase = original_phase

        spectator_client.emit("spectate", {"room_id": room_id})
        received = spectator_client.get_received()

        assert any(event["name"] == "spectate_enter" for event in received)
        spectate_state = next(
            event["args"][0]
            for event in received
            if event["name"] == "state_update" and event["args"][0].get("spectating")
        )
        assert spectate_state["room_id"] == room_id
        assert spectate_state["ai_test"] is True
        assert spectate_state["ai_match"] is True
        assert spectate_state["ai_player_id"] == 0
        assert spectate_state["ai_policy_label"] == "Phelren V1"
        assert spectate_state["player_names"] == ["Phelren", "Spectated Human"]
        assert spectate_state["player_avatar_kinds"] == ["phelren", ""]
        assert spectate_state["you"]["avatar_kind"] == "phelren"
        assert spectate_state["opponent"]["avatar_kind"] == ""
        assert spectate_state["spectator_count"] == 1
        assert spectate_state["spectator_players"][0]["nickname"] == "Watching Human"

        gtn.send_solo_state(owner_sid, 1)
        owner_state = next(
            event["args"][0]
            for event in owner_client.get_received()
            if event["name"] == "solo_state"
        )
        assert owner_state["room_id"] == room_id
        assert owner_state["ai_player_id"] == 0
        assert owner_state["player_avatar_kinds"] == ["phelren", ""]
        assert owner_state["opponent"]["avatar_kind"] == "phelren"
        assert owner_state["spectator_count"] == 1
        assert owner_state["spectator_players"][0]["nickname"] == "Watching Human"

        with mock.patch.object(gtn, "DB_AVAILABLE", False):
            spectator_client.emit("chat", {"text": "Phelren spectator chat"})
        owner_chat = next(
            event["args"][0]
            for event in owner_client.get_received()
            if event["name"] == "chat"
        )
        assert owner_chat["text"] == "Phelren spectator chat"
        assert owner_chat["is_spectator"] is True
        cached_chat = gtn.room_chat_history_for_sid(room, owner_sid)
        assert cached_chat["items"][-1]["text"] == "Phelren spectator chat"

        with gtn._lock:
            gtn._drop_solo_session_locked(owner_sid)
        leave_events = spectator_client.get_received()
        assert any(event["name"] == "spectate_leave" for event in leave_events)
        assert room_id not in gtn.rooms
        assert gtn.players[spectator_sid]["status"] == "lobby"
        assert gtn.players[spectator_sid]["spectating_room"] is None
    finally:
        with gtn._lock:
            gtn._drop_solo_session_locked(owner_sid)
        gtn.rooms.pop(room_id, None)
        gtn.players.pop(owner_sid, None)
        gtn.players.pop(spectator_sid, None)
        owner_client.disconnect()
        spectator_client.disconnect()


def test_ai_start_emits_loading_before_background_worker_is_ready():
    http_client = gtn.app.test_client()
    with http_client.session_transaction() as session:
        session["user_id"] = 102
    client = gtn.socketio.test_client(gtn.app, flask_test_client=http_client)
    room_map = gtn.socketio.server.manager.rooms["/"][None]
    sid = next(key for key, value in room_map.items() if value == client.eio_sid)
    gtn.players[sid] = {
        "nickname": "Loading Human",
        "user_id": 102,
        "is_registered_user": True,
        "status": "lobby",
        "room_id": None,
        "disabled_mods": [],
        "skin": {},
        "beta_mode": False,
        "mode": "1v1",
    }
    started = []
    try:
        with (
            mock.patch.object(gtn, "GTN_AI_1V1_TEST_ENABLED", True),
            mock.patch.object(gtn, "GTN_AI_PUBLIC_ENTRY_ENABLED", True),
            mock.patch.object(
                gtn,
                "_start_ai_test_background_task",
                side_effect=lambda queued_sid: started.append(queued_sid),
            ),
        ):
            client.emit("ai_1v1_start", {})
            received = client.get_received()

        assert started == [sid]
        assert [event["name"] for event in received] == ["ai_1v1_status"]
        assert received[0]["args"][0]["status"] == "loading"
        assert sid in gtn.ai_test_starting
        assert gtn.players[sid]["status"] == "lobby"
    finally:
        gtn.ai_test_starting.discard(sid)
        gtn._SOLO_ACTION_LOCKS.pop(sid, None)
        gtn.players.pop(sid, None)
        client.disconnect()


def test_guest_socket_cannot_start_public_ai_match():
    client = gtn.socketio.test_client(gtn.app, flask_test_client=gtn.app.test_client())
    room_map = gtn.socketio.server.manager.rooms["/"][None]
    sid = next(key for key, value in room_map.items() if value == client.eio_sid)
    gtn.players[sid] = {
        "nickname": "Guest Human",
        "status": "lobby",
        "room_id": None,
        "disabled_mods": [],
        "skin": {},
        "beta_mode": False,
        "mode": "1v1",
        "is_registered_user": False,
    }
    try:
        with (
            mock.patch.object(gtn, "GTN_AI_1V1_TEST_ENABLED", True),
            mock.patch.object(gtn, "GTN_AI_PUBLIC_ENTRY_ENABLED", True),
        ):
            client.get_received()
            client.emit("ai_1v1_start", {})
            received = client.get_received()

        payloads = [
            event["args"][0]
            for event in received
            if event["name"] == "ai_1v1_status"
        ]
        assert payloads[-1]["code"] == "account_required"
        assert sid not in gtn.ai_test_starting
    finally:
        gtn.ai_test_starting.discard(sid)
        gtn.players.pop(sid, None)
        client.disconnect()


def test_ai_start_rejects_when_active_capacity_is_full():
    http_client = gtn.app.test_client()
    with http_client.session_transaction() as session:
        session["user_id"] = 106
    client = gtn.socketio.test_client(gtn.app, flask_test_client=http_client)
    room_map = gtn.socketio.server.manager.rooms["/"][None]
    sid = next(key for key, value in room_map.items() if value == client.eio_sid)
    active_sid = "other-active-ai-session"
    gtn.players[sid] = {
        "nickname": "Waiting Human",
        "user_id": 106,
        "is_registered_user": True,
        "status": "lobby",
        "room_id": None,
        "disabled_mods": [],
        "skin": {},
        "beta_mode": False,
        "mode": "1v1",
    }
    gtn.solo_sessions[active_sid] = _test_engine()
    gtn.ai_test_sessions[active_sid] = {"session_id": "active-capacity-test"}
    try:
        with (
            mock.patch.object(gtn, "GTN_AI_1V1_TEST_ENABLED", True),
            mock.patch.object(gtn, "GTN_AI_PUBLIC_ENTRY_ENABLED", True),
            mock.patch.object(gtn, "GTN_AI_1V1_MAX_ACTIVE", 1),
        ):
            client.get_received()
            client.emit("ai_1v1_start", {})
            received = client.get_received()

        payloads = [
            event["args"][0]
            for event in received
            if event["name"] == "ai_1v1_status"
        ]
        assert payloads[-1]["code"] == "capacity"
        assert sid not in gtn.ai_test_starting
    finally:
        gtn.solo_sessions.pop(active_sid, None)
        gtn.ai_test_sessions.pop(active_sid, None)
        gtn.ai_test_starting.discard(sid)
        gtn.players.pop(sid, None)
        client.disconnect()


def test_finished_ai_result_screen_does_not_consume_active_capacity():
    sid = "finished-ai-capacity-test"
    engine = _test_engine()
    assert engine.surrender(0).get("success")
    gtn.solo_sessions[sid] = engine
    gtn.ai_test_sessions[sid] = {"session_id": "finished-capacity-test"}
    try:
        with gtn._lock:
            assert gtn._ai_test_active_count_locked() == 0
    finally:
        gtn.solo_sessions.pop(sid, None)
        gtn.ai_test_sessions.pop(sid, None)


def test_ai_surrender_emits_game_over_instead_of_pausing_into_solo_training():
    http_client = gtn.app.test_client()
    with http_client.session_transaction() as session:
        session["user_id"] = 107
    client = gtn.socketio.test_client(gtn.app, flask_test_client=http_client)
    room_map = gtn.socketio.server.manager.rooms["/"][None]
    sid = next(key for key, value in room_map.items() if value == client.eio_sid)
    engine = _test_engine()
    meta = {
        "session_id": "ai-surrender-session",
        "human_player_id": 0,
        "ai_player_id": 1,
        "human_name": "Surrendering Human",
        "ai_name": "Phelren",
        "diagnostic_finished": True,
    }
    gtn.players[sid] = {
        "nickname": "Surrendering Human",
        "user_id": 107,
        "is_registered_user": True,
        "status": "in_game",
        "room_id": None,
        "disabled_mods": [],
        "skin": {},
        "beta_mode": False,
        "mode": "1v1",
    }
    gtn.solo_sessions[sid] = engine
    gtn.ai_test_sessions[sid] = meta
    try:
        client.get_received()
        with mock.patch.object(gtn, "_maybe_finish_ai_test_session"):
            client.emit("surrender", {"match_key": gtn._ai_test_match_key(meta)})
            received = client.get_received()

        assert not any(event["name"] == "solo_paused" for event in received)
        phase_payload = next(
            event["args"][0] for event in received if event["name"] == "game_phase"
        )
        state_payload = next(
            event["args"][0] for event in received if event["name"] == "solo_state"
        )
        assert phase_payload["phase"] == "game_over"
        assert phase_payload["ai_test"] is True
        assert state_payload["phase"] == "game_over"
        assert state_payload["ai_test"] is True
        assert state_payload["winner"] == 1
        assert sid in gtn.solo_sessions
        assert sid in gtn.ai_test_sessions
    finally:
        gtn.solo_sessions.pop(sid, None)
        gtn.ai_test_sessions.pop(sid, None)
        gtn.ai_test_starting.discard(sid)
        gtn._SOLO_ACTION_LOCKS.pop(sid, None)
        gtn.players.pop(sid, None)
        client.disconnect()


def test_ai_game_over_can_return_to_lobby_and_clear_session():
    http_client = gtn.app.test_client()
    with http_client.session_transaction() as session:
        session["user_id"] = 103
    client = gtn.socketio.test_client(gtn.app, flask_test_client=http_client)
    room_map = gtn.socketio.server.manager.rooms["/"][None]
    sid = next(key for key, value in room_map.items() if value == client.eio_sid)
    engine = _test_engine()
    assert engine.surrender(0).get("success")
    meta = {
        "session_id": "ai-return-session",
        "human_player_id": 0,
        "ai_player_id": 1,
        "diagnostic_finished": True,
    }
    gtn.players[sid] = {
        "nickname": "Returning Human",
        "user_id": 103,
        "is_registered_user": True,
        "status": "solo",
        "room_id": None,
        "disabled_mods": [],
        "skin": {},
        "beta_mode": False,
        "mode": "1v1",
    }
    gtn.solo_sessions[sid] = engine
    gtn.ai_test_sessions[sid] = meta
    try:
        client.get_received()
        client.emit("return_lobby", {"match_key": gtn._ai_test_match_key(meta)})
        received = client.get_received()

        phase_payload = next(
            event["args"][0] for event in received if event["name"] == "game_phase"
        )
        assert phase_payload["phase"] == "lobby"
        assert phase_payload["solo"] is False
        assert phase_payload["ai_test"] is False
        assert sid not in gtn.solo_sessions
        assert sid not in gtn.ai_test_sessions
        assert gtn.players[sid]["status"] == "lobby"
    finally:
        gtn.solo_sessions.pop(sid, None)
        gtn.ai_test_sessions.pop(sid, None)
        gtn.ai_test_starting.discard(sid)
        gtn._SOLO_ACTION_LOCKS.pop(sid, None)
        gtn.players.pop(sid, None)
        client.disconnect()


def test_ai_game_over_rematch_queues_a_fresh_session():
    http_client = gtn.app.test_client()
    with http_client.session_transaction() as session:
        session["user_id"] = 104
    client = gtn.socketio.test_client(gtn.app, flask_test_client=http_client)
    room_map = gtn.socketio.server.manager.rooms["/"][None]
    sid = next(key for key, value in room_map.items() if value == client.eio_sid)
    engine = _test_engine()
    assert engine.surrender(0).get("success")
    gtn.players[sid] = {
        "nickname": "Rematch Human",
        "user_id": 104,
        "is_registered_user": True,
        "status": "solo",
        "room_id": None,
        "disabled_mods": [],
        "skin": {},
        "beta_mode": False,
        "mode": "1v1",
    }
    gtn.solo_sessions[sid] = engine
    gtn.ai_test_sessions[sid] = {
        "session_id": "ai-rematch-session",
        "human_player_id": 0,
        "ai_player_id": 1,
        "diagnostic_finished": True,
    }
    queued = []
    try:
        with (
            mock.patch.object(gtn, "GTN_AI_1V1_TEST_ENABLED", True),
            mock.patch.object(gtn, "GTN_AI_PUBLIC_ENTRY_ENABLED", True),
            mock.patch.object(
                gtn,
                "_start_ai_test_background_task",
                side_effect=lambda queued_sid: queued.append(queued_sid),
            ),
        ):
            client.get_received()
            client.emit("ai_1v1_rematch", {})
            received = client.get_received()

        assert queued == [sid]
        assert any(
            event["name"] == "ai_1v1_status"
            and event["args"][0]["status"] == "loading"
            for event in received
        )
        assert sid not in gtn.solo_sessions
        assert sid not in gtn.ai_test_sessions
        assert sid in gtn.ai_test_starting
        assert gtn.players[sid]["status"] == "lobby"
    finally:
        gtn.solo_sessions.pop(sid, None)
        gtn.ai_test_sessions.pop(sid, None)
        gtn.ai_test_starting.discard(sid)
        gtn._SOLO_ACTION_LOCKS.pop(sid, None)
        gtn.players.pop(sid, None)
        client.disconnect()


def test_ai_match_runs_formal_event_and_card_draft_before_combat():
    http_client = gtn.app.test_client()
    with http_client.session_transaction() as session:
        session["user_id"] = 105
    client = gtn.socketio.test_client(gtn.app, flask_test_client=http_client)
    room_map = gtn.socketio.server.manager.rooms["/"][None]
    sid = next(key for key, value in room_map.items() if value == client.eio_sid)
    gtn.players[sid] = {
        "nickname": "Draft Human",
        "user_id": 105,
        "is_registered_user": True,
        "status": "lobby",
        "room_id": None,
        "disabled_mods": [],
        "skin": {},
        "beta_mode": False,
        "mode": "1v1",
    }
    try:
        with (
            mock.patch.object(gtn, "GTN_AI_1V1_TEST_ENABLED", True),
            mock.patch.object(gtn, "GTN_AI_PUBLIC_ENTRY_ENABLED", True),
            mock.patch.object(gtn, "get_local_ai_worker", return_value=_StartOnlyWorker()),
            mock.patch.object(gtn.secrets, "randbelow", return_value=0),
            mock.patch.object(gtn.secrets, "randbits", return_value=81723),
            mock.patch.object(gtn, "_start_socket_background_task", return_value=None),
            mock.patch.object(gtn.socketio, "sleep") as sleep_mock,
            mock.patch.object(
                gtn,
                "_start_ai_test_background_task",
                side_effect=gtn._start_ai_test_session,
            ),
        ):
            client.emit("ai_1v1_start", {})
            opening_events = client.get_received()
            event_payload = next(
                event["args"][0] for event in opening_events if event["name"] == "event_select"
            )
            assert event_payload["events"]
            assert event_payload["pregame_timer_status"] == "event_select"
            assert 0 < int(event_payload["pregame_timer_remaining"]) <= int(
                gtn.EVENT_SELECT_TIMEOUT_SECONDS
            )
            assert int(event_payload["pregame_timer_total"]) == int(
                gtn.EVENT_SELECT_TIMEOUT_SECONDS
            )
            assert event_payload["pregame_timer_paused"] is False
            gtn._run_ai_test_pregame(sid)
            client.get_received()

            client.emit("select_opening_event", {"event_id": event_payload["events"][0]["id"]})
            reveal_events = client.get_received()
            assert "event_reveal" in [event["name"] for event in reveal_events]

            client.emit("confirm_opening_reveal", {})
            draft_events = client.get_received()
            draft_payload = next(
                event["args"][0] for event in draft_events if event["name"] == "draft_state"
            )
            assert draft_payload["pregame_timer_status"] == "drafting"
            assert int(draft_payload["pregame_timer_remaining"]) > 0
            assert int(draft_payload["pregame_timer_total"]) >= int(
                gtn.DRAFT_INITIAL_TIMEOUT_SECONDS
            )
            assert draft_payload["pregame_timer_paused"] is False
            gtn._run_ai_test_pregame(sid)
            client.get_received()
            total_rounds = int(draft_payload["total_rounds"])
            engine = gtn.solo_sessions[sid]
            meta = gtn.ai_test_sessions[sid]
            human_player_id = int(meta["human_player_id"])
            ai_player_id = int(meta["ai_player_id"])
            ai_total_rounds = int(engine.draft_target_count(ai_player_id))
            assert total_rounds > 0
            assert ai_total_rounds > 0
            assert int(next(iter(draft_payload["others_total_rounds"].values()))) == ai_total_rounds
            assert len(sleep_mock.call_args_list) == ai_total_rounds + 1
            assert (
                gtn.AI_TEST_PREGAME_DELAY_MIN_SECONDS
                <= sleep_mock.call_args_list[0].args[0]
                <= gtn.AI_TEST_PREGAME_DELAY_MAX_SECONDS
            )
            assert all(
                gtn.AI_TEST_CARD_DELAY_MIN_SECONDS <= call.args[0] <= gtn.AI_TEST_CARD_DELAY_MAX_SECONDS
                for call in sleep_mock.call_args_list[1:]
            )
            initial_rerolls = int(draft_payload["rerolls"])
            if initial_rerolls > 0:
                client.emit("draft_reroll", {})
                reroll_events = client.get_received()
                draft_payload = next(
                    event["args"][0]
                    for event in reroll_events
                    if event["name"] == "draft_state"
                )
                assert int(draft_payload["rerolls"]) == initial_rerolls - 1

            final_events = []
            for _ in range(total_rounds):
                assert draft_payload["options"]
                client.emit("draft_pick", {"def_id": draft_payload["options"][0]["def_id"]})
                final_events = client.get_received()
                next_draft = [
                    event["args"][0]
                    for event in final_events
                    if event["name"] == "draft_state"
                ]
                if next_draft:
                    draft_payload = next_draft[-1]

            names = [event["name"] for event in final_events]
            if "event_sub_choice" in names:
                client.emit("submit_event_sub_choice", {
                    "sub_choice": gtn._default_event_sub_choice(engine, human_player_id),
                })
                final_events = client.get_received()
                names = [event["name"] for event in final_events]
            assert "solo_state" in names
            state = next(event["args"][0] for event in final_events if event["name"] == "solo_state")
            assert state["phase"] == "action"
            assert state["solo"] is True
            assert state["ai_test"] is True
            assert state["your_name"] == "Draft Human"
            assert state["opponent_name"] == "Phelren"
            assert state["match_key"] == event_payload["match_key"]
            assert state["turn_timer_player"] == state["current_player"]
            assert int(state["turn_timer_remaining"]) > 0
            assert int(state["turn_timer_total"]) == int(gtn.ACTION_TURN_SECONDS)
            assert len(engine.draft_picks[human_player_id]) == total_rounds
            assert len(engine.draft_picks[ai_player_id]) == ai_total_rounds

            client.emit("request_game_state", {})
            refresh_events = client.get_received()
            refreshed_state = next(
                event["args"][0] for event in refresh_events if event["name"] == "solo_state"
            )
            assert refreshed_state["match_key"] == state["match_key"]
    finally:
        gtn.solo_sessions.pop(sid, None)
        gtn.ai_test_sessions.pop(sid, None)
        gtn._SOLO_ACTION_LOCKS.pop(sid, None)
        gtn.players.pop(sid, None)
        client.disconnect()


def test_ai_match_uses_formal_controls_without_training_tools():
    source = (Path(gtn.__file__).parent / "static" / "js" / "game.js").read_text(encoding="utf-8")
    assert "const inSoloTraining = inSoloGame && !inAiTest;" in source
    assert "showSoloNextDraw = inSoloTraining" in source
    assert "showSoloEdit = inSoloTraining" in source
    assert "(!inSoloGame || inAiTest) && !gameOver" in source
    assert "classList.toggle('mode-solo', !!gs.solo && !gs.ai_test)" in source
    assert "if (data.ai_test)" in source
    assert "{ fullScreen: true, tutorial: false }" in source
    assert "socket.emit('ai_1v1_rematch', {})" in source
    assert "if (gameState?.ai_test) socket.emit('surrender', currentMatchActionContext());" in source
    assert "setAi1v1TestLoading(true)" in source
    assert "markRecentAiDecision" not in source
    assert "ai-test-mark-decision" not in source
    assert "确认与 Phelren 进行 1v1 对局？本场对局不计花阶分。" in source
    assert "if (!!gs.solo && !gs.ai_test && gs.phase === 'game_over')" in source
    assert "if (inSoloGame && !gs.ai_test && gs.phase === 'game_over' && playZone)" in source
    assert "const aiMatch = !!(gs && gs.ai_test);" in source
    assert "&& (!soloMode || aiMatch)" in source
    assert "const PHELREN_AVATAR_KIND = 'phelren';" in source
    assert "class=\"phelren-avatar-frame\"" in source
    assert "resolveBattlePlayerAvatarKind" in source
    avatar = Path(gtn.__file__).parent / "static" / "assets" / "player-avatars" / "phelren-frame.svg"
    assert avatar.is_file()
    assert "#898989" in avatar.read_text(encoding="utf-8")
    css = (Path(gtn.__file__).parent / "static" / "css" / "style.css").read_text(encoding="utf-8")
    assert ".skin-avatar.phelren-avatar .skin-eye" in css
    assert ".skin-avatar.phelren-avatar .skin-mouth" in css
    assert "top: 35%;" in css
    assert "left: 35%;" in css
    assert "right: 35%;" in css
    assert "top: 62.5%;" in css


def test_ai_match_pregame_timeout_uses_formal_auto_selection():
    sid = "ai-pregame-timeout-test"
    gtn.players[sid] = {
        "nickname": "Timeout Human",
        "status": "solo",
        "room_id": None,
        "disabled_mods": [],
        "skin": {},
        "beta_mode": False,
        "mode": "1v1",
    }
    engine, _, enabled_mods, human_name, ai_name, ai_event_id = gtn._create_ai_test_engine(
        sid,
        human_player_id=0,
        seed=7123,
    )
    meta = {
        "session_id": "ai-pregame-timeout-session",
        "created_at_ts": gtn.time.time(),
        "seed": 7123,
        "human_player_id": 0,
        "ai_player_id": 1,
        "human_name": human_name,
        "ai_name": ai_name,
        "enabled_mods": enabled_mods,
        "ai_opening_event_id": ai_event_id,
        "diagnostic_metadata": {},
    }
    gtn.solo_sessions[sid] = engine
    gtn.ai_test_sessions[sid] = meta
    room = gtn._create_ai_test_replay_room(sid, engine, meta)
    meta["replay_room"] = room
    deadline = gtn.time.time() - 1
    room.pregame_deadlines[(0, "event_select")] = deadline

    try:
        with mock.patch.object(gtn, "DB_AVAILABLE", False):
            tick = gtn._tick_ai_test_match_timer(sid, now=deadline + 2)

        assert tick["kind"] == "pregame"
        assert tick["status"] == "event_select"
        assert tick["advanced"] is True
        assert tick["schedule_ai"] is True
        assert engine.opening_event_picks[0] is not None
        assert room.record_pregame_stats is False
        assert room._replay_actions[-1]["type"] == "select_opening_event"
        assert room._replay_actions[-1]["actor"] == 0
    finally:
        gtn.solo_sessions.pop(sid, None)
        gtn.ai_test_sessions.pop(sid, None)
        gtn._SOLO_ACTION_LOCKS.pop(sid, None)
        gtn.players.pop(sid, None)
