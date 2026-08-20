import os
from pathlib import Path
from unittest import mock

import pytest

from ai_local_bridge import LocalAiBridgeTimeout, LocalAiWorkerClient
from game_engine import GameEngine


def test_local_ai_bridge_engine_codec_round_trip() -> None:
    engine = GameEngine()
    encoded = LocalAiWorkerClient.encode_engine(engine)
    restored = LocalAiWorkerClient.decode_engine(encoded)

    assert isinstance(restored, GameEngine)
    assert restored.get_public_state(0) == engine.get_public_state(0)


def test_local_ai_bridge_command_is_loopback_and_uses_isolated_python(tmp_path) -> None:
    game_root = tmp_path / "game"
    ai_root = tmp_path / "GTN-AI"
    game_root.mkdir()
    client = LocalAiWorkerClient(game_root=game_root, ai_root=ai_root)
    command = client._command()

    assert command[0].endswith("GTN-AI\\.venv\\Scripts\\python.exe")
    assert command[command.index("--host") + 1] == "127.0.0.1"
    assert "--token" in command
    assert command[command.index("--max-sessions") + 1] == "8"
    assert command[command.index("--retention-days") + 1] == "14.0"


def test_local_ai_bridge_discovers_posix_virtualenv(tmp_path) -> None:
    game_root = tmp_path / "game"
    ai_root = tmp_path / "GTN-AI"
    python = ai_root / ".venv" / "bin" / "python"
    game_root.mkdir()
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")

    client = LocalAiWorkerClient(game_root=game_root, ai_root=ai_root)

    assert client.python == Path(os.path.abspath(python))


@pytest.mark.skipif(os.name == "nt", reason="POSIX venvs use python symlinks")
def test_local_ai_bridge_preserves_virtualenv_python_symlink(tmp_path) -> None:
    game_root = tmp_path / "game"
    ai_root = tmp_path / "GTN-AI"
    system_python = tmp_path / "system" / "python3"
    venv_python = ai_root / ".venv" / "bin" / "python"
    game_root.mkdir()
    system_python.parent.mkdir()
    system_python.write_text("", encoding="utf-8")
    venv_python.parent.mkdir(parents=True)
    venv_python.symlink_to(system_python)

    client = LocalAiWorkerClient(game_root=game_root, ai_root=ai_root)

    assert client.python == Path(os.path.abspath(venv_python))
    assert client.python != system_python.resolve()


def test_local_ai_bridge_accepts_server_paths_and_retention_settings(tmp_path) -> None:
    game_root = tmp_path / "game"
    ai_root = tmp_path / "ai"
    python = tmp_path / "python"
    runtime = tmp_path / "runtime"
    diagnostics = tmp_path / "diagnostics"
    game_root.mkdir()
    ai_root.mkdir()
    client = LocalAiWorkerClient(
        game_root=game_root,
        ai_root=ai_root,
        python_executable=python,
        runtime_root=runtime,
        diagnostics_root=diagnostics,
        max_sessions=4,
        retention_days=7,
        max_diagnostic_bytes=123456,
        export_finished=False,
        max_parallel_decisions=2,
    )
    command = client._command()

    assert command[0] == str(python.resolve())
    assert command[command.index("--diagnostics-root") + 1] == str(diagnostics.resolve())
    assert command[command.index("--max-sessions") + 1] == "4"
    assert command[command.index("--max-diagnostic-bytes") + 1] == "123456"
    assert "--export-finished" not in command
    assert client.max_parallel_decisions == 2


def test_local_ai_bridge_recycles_a_worker_after_decision_timeout(tmp_path) -> None:
    game_root = tmp_path / "game"
    ai_root = tmp_path / "ai"
    game_root.mkdir()
    ai_root.mkdir()
    client = LocalAiWorkerClient(game_root=game_root, ai_root=ai_root)
    engine = GameEngine()

    with (
        mock.patch.object(client, "start"),
        mock.patch.object(client, "_request", side_effect=LocalAiBridgeTimeout("late")),
        mock.patch.object(client, "stop") as stop,
        pytest.raises(LocalAiBridgeTimeout),
    ):
        client.decide_and_execute(
            engine,
            session_id="timeout-test",
            player_id=0,
            seed=1,
        )

    stop.assert_called_once_with()
