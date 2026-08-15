from __future__ import annotations

import atexit
import base64
import gzip
import json
import os
import pickle
import secrets
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class LocalAiBridgeError(RuntimeError):
    pass


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return int(default)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


class LocalAiWorkerClient:
    """Lazy client for the isolated loopback-only GTN-AI worker."""

    def __init__(
        self,
        *,
        game_root: str | Path | None = None,
        ai_root: str | Path | None = None,
        python_executable: str | Path | None = None,
        runtime_root: str | Path | None = None,
        diagnostics_root: str | Path | None = None,
        policy: str | None = None,
        startup_timeout: float = 90.0,
        request_timeout: float = 30.0,
        max_sessions: int | None = None,
        retention_days: float | None = None,
        max_diagnostic_bytes: int | None = None,
        export_finished: bool | None = None,
        max_parallel_decisions: int | None = None,
    ) -> None:
        self.game_root = Path(game_root or Path(__file__).resolve().parent).resolve()
        configured_ai_root = ai_root or os.environ.get("GTN_AI_ROOT")
        self.ai_root = Path(configured_ai_root or self.game_root.parent / "GTN-AI").resolve()
        self.python = self._resolve_python(python_executable)
        self.policy = str(policy or os.environ.get("GTN_AI_LIVE_POLICY") or "")
        self.startup_timeout = max(5.0, float(startup_timeout))
        self.request_timeout = max(1.0, float(request_timeout))
        configured_runtime = runtime_root or os.environ.get("GTN_AI_RUNTIME_ROOT")
        self.runtime_root = Path(configured_runtime or self.ai_root / ".runtime" / "live").resolve()
        configured_diagnostics = diagnostics_root or os.environ.get("GTN_AI_DIAGNOSTICS_ROOT")
        self.diagnostics_root = Path(
            configured_diagnostics or self.runtime_root / "human-sessions"
        ).resolve()
        self.max_sessions = max(1, int(
            max_sessions if max_sessions is not None else _env_int("GTN_AI_MAX_SESSIONS", 8)
        ))
        self.retention_days = max(0.0, float(
            retention_days
            if retention_days is not None
            else _env_float("GTN_AI_DIAGNOSTIC_RETENTION_DAYS", 14.0)
        ))
        if max_diagnostic_bytes is None:
            max_gb = max(0.0, _env_float("GTN_AI_DIAGNOSTIC_MAX_GB", 2.0))
            max_diagnostic_bytes = int(max_gb * 1024 * 1024 * 1024)
        self.max_diagnostic_bytes = max(0, int(max_diagnostic_bytes))
        self.export_finished = (
            _env_bool("GTN_AI_EXPORT_FINISHED", True)
            if export_finished is None
            else bool(export_finished)
        )
        decision_limit = max_parallel_decisions
        if decision_limit is None:
            decision_limit = _env_int("GTN_AI_MAX_PARALLEL_DECISIONS", 1)
        self.max_parallel_decisions = max(1, int(decision_limit))
        self._decision_slots = threading.BoundedSemaphore(self.max_parallel_decisions)
        self.ready_file = self.runtime_root / f"worker-{os.getpid()}-{secrets.token_hex(4)}.json"
        self.log_path = self.runtime_root / "worker.log"
        self._token = secrets.token_urlsafe(32)
        self._process: subprocess.Popen | None = None
        self._port: int | None = None
        self._log_handle = None
        self._lock = threading.RLock()
        atexit.register(self.stop)

    def _resolve_python(self, value: str | Path | None) -> Path:
        configured = value or os.environ.get("GTN_AI_PYTHON")
        if configured:
            return Path(configured).expanduser().resolve()
        candidates = [
            self.ai_root / ".venv" / "Scripts" / "python.exe",
            self.ai_root / ".venv" / "bin" / "python",
            self.ai_root / "venv" / "bin" / "python",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        return candidates[0 if os.name == "nt" else 1].resolve()

    @staticmethod
    def encode_engine(engine) -> str:
        raw = pickle.dumps(engine, protocol=5)
        return base64.b64encode(gzip.compress(raw, compresslevel=3)).decode("ascii")

    @staticmethod
    def decode_engine(payload: str):
        compressed = base64.b64decode(str(payload).encode("ascii"), validate=True)
        return pickle.loads(gzip.decompress(compressed))

    def _command(self) -> list[str]:
        command = [
            str(self.python),
            "-m",
            "gtn_ai.live_worker",
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--token",
            self._token,
            "--ready-file",
            str(self.ready_file),
            "--game-root",
            str(self.game_root),
            "--diagnostics-root",
            str(self.diagnostics_root),
            "--max-sessions",
            str(self.max_sessions),
            "--retention-days",
            str(self.retention_days),
            "--max-diagnostic-bytes",
            str(self.max_diagnostic_bytes),
        ]
        if self.export_finished:
            command.append("--export-finished")
        if self.policy:
            command.extend(["--policy", self.policy])
        return command

    def start(self) -> None:
        with self._lock:
            if self._process is not None and self._process.poll() is None and self._port:
                return
            if not self.python.is_file():
                raise LocalAiBridgeError(f"GTN-AI Python not found: {self.python}")
            if not (self.ai_root / "gtn_ai" / "live_worker.py").is_file():
                raise LocalAiBridgeError(f"GTN-AI live worker not found: {self.ai_root}")
            self.runtime_root.mkdir(parents=True, exist_ok=True)
            self.diagnostics_root.mkdir(parents=True, exist_ok=True)
            self.ready_file.unlink(missing_ok=True)
            self._log_handle = self.log_path.open("a", encoding="utf-8")
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self._process = subprocess.Popen(
                self._command(),
                cwd=str(self.ai_root),
                stdin=subprocess.DEVNULL,
                stdout=self._log_handle,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
            )

        deadline = time.monotonic() + self.startup_timeout
        last_error = ""
        while time.monotonic() < deadline:
            process = self._process
            if process is None or process.poll() is not None:
                raise LocalAiBridgeError(
                    f"GTN-AI worker exited during startup (code={getattr(process, 'returncode', None)})"
                )
            if self.ready_file.is_file():
                try:
                    ready = json.loads(self.ready_file.read_text(encoding="utf-8"))
                    self._port = int(ready["port"])
                    self._request("GET", "/health", None, timeout=2.0)
                    return
                except Exception as exc:
                    last_error = str(exc)
            time.sleep(0.1)
        self.stop()
        raise LocalAiBridgeError(f"GTN-AI worker startup timed out: {last_error}")

    def stop(self) -> None:
        with self._lock:
            process = self._process
            if self._port is not None:
                try:
                    self._request("POST", "/shutdown", {}, timeout=2.0)
                except Exception:
                    pass
            if process is not None and process.poll() is None:
                try:
                    process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=3.0)
                    except subprocess.TimeoutExpired:
                        process.kill()
            self._process = None
            self._port = None
            self.ready_file.unlink(missing_ok=True)
            if self._log_handle is not None:
                self._log_handle.close()
                self._log_handle = None

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        if self._port is None:
            raise LocalAiBridgeError("GTN-AI worker is not ready")
        body = None if payload is None else json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{self._port}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.request_timeout if timeout is None else timeout,
            ) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8")).get("error")
            except Exception:
                detail = str(exc)
            raise LocalAiBridgeError(f"GTN-AI request failed: {detail}") from exc
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise LocalAiBridgeError(f"GTN-AI worker is unavailable: {exc}") from exc
        if not result.get("success"):
            raise LocalAiBridgeError(str(result.get("error") or "GTN-AI request failed"))
        return result

    def decide_and_execute(
        self,
        engine,
        *,
        session_id: str,
        player_id: int,
        seed: int,
        enabled_mods: list[str] | None = None,
        public_history: list[dict[str, Any]] | None = None,
        session_metadata: dict[str, Any] | None = None,
    ) -> tuple[Any, dict[str, Any]]:
        self.start()
        acquired = self._decision_slots.acquire(timeout=self.request_timeout + 5.0)
        if not acquired:
            raise LocalAiBridgeError("Phelren decision capacity is busy")
        try:
            result = self._request("POST", "/v1/live/decide", {
                "session_id": session_id,
                "engine_snapshot": self.encode_engine(engine),
                "player_id": int(player_id),
                "seed": int(seed),
                "enabled_mods": list(enabled_mods or []),
                "public_history": list(public_history or []),
                "session_metadata": dict(session_metadata or {}),
                "record": True,
                "execute": True,
            })
        finally:
            self._decision_slots.release()
        snapshot = result.get("engine_snapshot")
        if not snapshot:
            raise LocalAiBridgeError("GTN-AI worker returned no updated engine")
        return self.decode_engine(snapshot), result

    def record_external(
        self,
        engine,
        *,
        session_id: str,
        player_id: int,
        action: dict[str, Any],
        seed: int,
        actor_kind: str = "human",
        session_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.start()
        return self._request("POST", "/v1/live/record", {
            "session_id": session_id,
            "engine_snapshot": self.encode_engine(engine),
            "player_id": int(player_id),
            "seed": int(seed),
            "actor_kind": actor_kind,
            "action": dict(action),
            "session_metadata": dict(session_metadata or {}),
        })

    def mark(
        self,
        *,
        session_id: str,
        decision_id: int | None = None,
        label: str = "review",
        note: str = "",
    ) -> dict[str, Any]:
        self.start()
        return self._request("POST", "/v1/live/mark", {
            "session_id": session_id,
            "decision_id": decision_id,
            "label": label,
            "note": note,
        })

    def finish(self, *, session_id: str, outcome: dict[str, Any] | None = None) -> dict[str, Any]:
        self.start()
        return self._request("POST", "/v1/live/finish", {
            "session_id": session_id,
            "outcome": dict(outcome or {}),
        })


_CLIENT: LocalAiWorkerClient | None = None
_CLIENT_LOCK = threading.Lock()


def get_local_ai_worker() -> LocalAiWorkerClient:
    global _CLIENT
    with _CLIENT_LOCK:
        if _CLIENT is None:
            _CLIENT = LocalAiWorkerClient()
        return _CLIENT
