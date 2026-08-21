import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
BASE_ENV_FILES = (
    "/etc/gtn/shared.env",
    "/etc/gtn/release.env",
    "/etc/gtn/ai.env",
)
INSTANCE_KEYS = {
    "GTN_INSTANCE",
    "GTN_INSTANCE_ID",
    "GTN_VERSION",
    "GTN_GIT_SHA",
    "GTN_STATIC_VERSION",
    "GTN_BIND_HOST",
    "GTN_PORT",
    "GTN_DRAIN_FILE",
    "GTN_SYSTEMD_SERVICE",
    "GTN_DB_MAINTENANCE_ENABLED",
}


def _read(name):
    return (SCRIPTS / name).read_text(encoding="utf-8")


def _assert_in_order(source, values):
    positions = [source.index(value) for value in values]
    assert positions == sorted(positions)


def _instance_env_keys(script):
    match = re.search(
        r'cat > "\$INSTANCE_ENV_TMP" <<EOF\n(?P<body>.*?)\nEOF',
        script,
        flags=re.DOTALL,
    )
    assert match, "instance override heredoc is missing"
    keys = {
        line.split("=", 1)[0]
        for line in match.group("body").splitlines()
        if line.startswith("GTN_") and "=" in line
    }
    return keys, match.group("body")


def _prepared_output(script):
    match = re.search(
        r"cat <<EOF\n\nPrepared\.\n(?P<body>.*?)\nEOF\s*\Z",
        script,
        flags=re.DOTALL,
    )
    assert match, "final operator instructions heredoc is missing"
    return match.group("body")


def _environment_order_instructions(output):
    match = re.search(
        r"this order \(later files override earlier files\):\n(?P<body>(?:  \$[A-Z_]+\n){4})",
        output,
    )
    assert match, "environment precedence instructions are missing"
    return match.group("body")


def _bash_env(**overrides):
    env = {"PATH": os.environ.get("PATH", "")}
    env.update(overrides)
    return env


def test_blue_green_service_template_loads_required_environment_in_order():
    template = _read("gtn-blue-green.service.template")
    env_files = re.findall(r"^EnvironmentFile=(.+)$", template, flags=re.MULTILINE)
    assert env_files == [
        *BASE_ENV_FILES,
        "/etc/gtn/gtn-release-next.env",
    ]
    assert not re.search(r"^Environment=GTN_", template, flags=re.MULTILINE)


def test_automated_prepare_writes_non_secret_override_and_strict_health_checks():
    script = _read("gtn_prepare_next.sh")
    keys, body = _instance_env_keys(script)
    assert keys == INSTANCE_KEYS
    assert "SECRET" not in body
    assert "R2_" not in body
    assert "GTN_AI_" not in body
    assert 'chmod 0640 "$INSTANCE_ENV_TMP"' in script
    assert 'chown root:root "$INSTANCE_ENV_TMP"' in script
    assert 'mv -f -- "$INSTANCE_ENV_TMP" "$INSTANCE_ENV_FILE"' in script
    assert script.index("python -m py_compile") < script.index(
        'mv -f -- "$INSTANCE_ENV_TMP" "$INSTANCE_ENV_FILE"'
    )
    assert 'UNIT_TMP="$(mktemp "/etc/systemd/system/.${SERVICE_NAME}.service.XXXXXX")"' in script
    assert 'mv -f -- "$UNIT_TMP" "$UNIT_FILE"' in script
    assert "realpath -m" in script
    assert "Release, next, and environment directories must be separate, non-nested paths" in script
    assert "Next service must differ from current service" in script
    assert "Next port must differ from current port" in script
    assert "git check-ref-format" in script
    assert 'git clone --origin "$REMOTE_NAME" --branch "$BRANCH"' in script
    assert 'fetch "$REMOTE_NAME"' in script
    assert "Existing next directory is not a marked disposable GTN checkout" in script
    assert 'install -m 0600 /dev/null "$TARGET_MARKER"' in script
    assert "clean -fd -e venv -e .venv -e .gtn-blue-green-target" in script
    assert script.index("Existing next directory is not a marked disposable GTN checkout") < script.index(
        'remote set-url "$REMOTE_NAME"'
    )
    assert script.index("Release, next, and environment directories must be separate, non-nested paths") < script.index(
        "git clone"
    )
    assert "mktemp -d /tmp/gtn-prepare-health.XXXXXX" in script
    assert 'HEALTH_JSON="$HEALTH_TMP_DIR/health.json"' in script
    assert "trap cleanup_prepare_tmp EXIT" in script
    assert '/tmp/gtn-${SERVICE_NAME}-health.json' not in script
    _assert_in_order(
        script,
        (
            "EnvironmentFile=${SHARED_ENV_FILE}",
            "EnvironmentFile=${RELEASE_ENV_FILE}",
            "EnvironmentFile=${AI_ENV_FILE}",
            "EnvironmentFile=${INSTANCE_ENV_FILE}",
        ),
    )
    for field in ("instance_id", "version", "git_sha", "port", "draining"):
        assert f"payload.get('{field}')" in script
    assert "/api/health/full" in script
    assert "payload.get('db_ok') is True" in script
    assert "payload.get('socket_ok') is True" in script
    assert "/api/ai-1v1/status" in script
    assert "payload.get('enabled') is True" in script


def test_manual_prepare_writes_same_override_and_does_not_suggest_bare_python():
    script = _read("blue_green_prepare.sh")
    output = _prepared_output(script)
    keys, body = _instance_env_keys(script)
    assert keys == INSTANCE_KEYS
    assert "SECRET" not in body
    assert "R2_" not in body
    assert "GTN_AI_" not in body
    assert './venv/bin/python app.py' not in script
    assert "realpath -m" in script
    assert "Next service must differ from current service" in script
    assert "Next port must differ from current port" in script
    assert "Source, target, and environment directories must be separate, non-nested paths" in script
    assert script.index("Source, target, and environment directories must be separate, non-nested paths") < script.index(
        "rsync -a --delete"
    )
    assert '.gtn-blue-green-target' in script
    assert script.index("not marked as a disposable GTN next instance") < script.index("rsync -a --delete")
    _assert_in_order(
        _environment_order_instructions(output),
        (
            "$SHARED_ENV_FILE",
            "$RELEASE_ENV_FILE",
            "$AI_ENV_FILE",
            "$INSTANCE_ENV_FILE",
        ),
    )


def test_deployment_guide_documents_environment_precedence_and_validation():
    guide = _read("BLUE_GREEN_DEPLOY.md")
    _assert_in_order(guide, (*BASE_ENV_FILES, "/etc/gtn/gtn-release-next.env"))
    assert "不要用裸 `python app.py`" in guide
    assert "`db_ok=true`、`socket_ok=true`" in guide
    assert "`enabled=true`" in guide
    assert ".gtn-blue-green-target" in guide


@pytest.mark.skipif(os.name == "nt" or shutil.which("bash") is None, reason="requires Linux bash")
@pytest.mark.parametrize("name", ("gtn_prepare_next.sh", "blue_green_prepare.sh"))
@pytest.mark.parametrize("next_service", ("gtn-release.service", "gtn-release.service.service"))
def test_prepare_rejects_current_service_aliases(name, next_service):
    env = _bash_env(
        GTN_NEXT_SERVICE=next_service,
        GTN_CURRENT_SERVICE="gtn-release",
    )
    result = subprocess.run(
        ["bash", str(SCRIPTS / name)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 2
    assert "Next service must differ from current service" in result.stderr


@pytest.mark.skipif(os.name == "nt" or shutil.which("bash") is None, reason="requires Linux bash")
def test_automated_prepare_rejects_environment_nested_under_next_before_checkout():
    result = subprocess.run(
        ["bash", str(SCRIPTS / "gtn_prepare_next.sh")],
        capture_output=True,
        text=True,
        check=False,
        env=_bash_env(
            GTN_RELEASE_DIR="/does-not-exist-release",
            GTN_NEXT_DIR="/does-not-exist-next",
            GTN_ENV_DIR="/does-not-exist-next/env",
        ),
    )
    assert result.returncode == 2
    assert "directories must be separate, non-nested paths" in result.stderr


@pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None or shutil.which("git") is None,
    reason="requires Linux bash and git",
)
def test_automated_prepare_rejects_unmarked_unrelated_git_repo_before_mutation(tmp_path):
    release = tmp_path / "release"
    release.mkdir()
    subprocess.run(["git", "init", "-q", str(release)], check=True)
    (release / "app.py").write_text("", encoding="utf-8")
    (release / "requirements.txt").write_text("", encoding="utf-8")

    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    subprocess.run(["git", "init", "-q", str(unrelated)], check=True)
    sentinel = unrelated / "keep-me.txt"
    sentinel.write_text("unrelated repository", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(SCRIPTS / "gtn_prepare_next.sh")],
        capture_output=True,
        text=True,
        check=False,
        env=_bash_env(
            GTN_RELEASE_DIR=str(release),
            GTN_NEXT_DIR=str(unrelated),
            GTN_ENV_DIR=str(tmp_path / "env"),
            GTN_GIT_URL="https://invalid.example/should-not-be-used.git",
        ),
    )

    assert result.returncode == 1
    assert "not a marked disposable GTN checkout" in result.stderr
    assert sentinel.read_text(encoding="utf-8") == "unrelated repository"
    remotes = subprocess.run(
        ["git", "-C", str(unrelated), "remote"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert remotes.stdout.strip() == ""


@pytest.mark.skipif(os.name == "nt" or shutil.which("bash") is None, reason="requires Linux bash")
@pytest.mark.parametrize(
    ("source", "target", "env_dir", "expected_code"),
    (
        ("/", "/does-not-exist-target", "/does-not-exist-env", 2),
        (
            "/does-not-exist-source",
            "/does-not-exist-target",
            "/does-not-exist-target/env",
            1,
        ),
    ),
)
def test_manual_prepare_rejects_root_or_nested_environment_before_rsync(
    source, target, env_dir, expected_code
):
    result = subprocess.run(
        ["bash", str(SCRIPTS / "blue_green_prepare.sh"), source, target, "5002", "release"],
        capture_output=True,
        text=True,
        check=False,
        env=_bash_env(GTN_ENV_DIR=env_dir),
    )
    assert result.returncode == expected_code
    assert "rsync" not in result.stderr


@pytest.mark.skipif(os.name == "nt" or shutil.which("bash") is None, reason="bash -n requires Linux bash")
@pytest.mark.parametrize(
    "name",
    ("gtn_prepare_next.sh", "blue_green_prepare.sh", "gtn_healthcheck.sh"),
)
def test_deployment_shell_syntax(name):
    result = subprocess.run(
        ["bash", "-n", str(SCRIPTS / name)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
