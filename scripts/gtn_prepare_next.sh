#!/usr/bin/env bash
set -euo pipefail

# Prepare and start a blue-green "next" instance without touching the current
# release process or nginx routing.
#
# Defaults match the Aliyun GTN server:
#   current release: /opt/gtn-release on 127.0.0.1:5000
#   next instance:   /opt/gtn-next    on 127.0.0.1:5002

RELEASE_DIR="${GTN_RELEASE_DIR:-/opt/gtn-release}"
NEXT_DIR="${GTN_NEXT_DIR:-/opt/gtn-next}"
SERVICE_NAME="${GTN_NEXT_SERVICE:-gtn-release-next}"
PORT="${GTN_NEXT_PORT:-5002}"
CURRENT_SERVICE="${GTN_CURRENT_SERVICE:-gtn-release}"
CURRENT_PORT="${GTN_CURRENT_PORT:-5000}"
INSTANCE="${GTN_INSTANCE:-release}"
BRANCH="${GTN_GIT_BRANCH:-main}"
REMOTE_NAME="${GTN_GIT_REMOTE:-origin}"
REMOTE_URL="${GTN_GIT_URL:-}"
ENV_DIR="${GTN_ENV_DIR:-/etc/gtn}"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<EOF
Usage:
  gtn_prepare_next.sh

Environment overrides:
  GTN_RELEASE_DIR=/opt/gtn-release
  GTN_NEXT_DIR=/opt/gtn-next
  GTN_NEXT_SERVICE=gtn-release-next
  GTN_NEXT_PORT=5002
  GTN_CURRENT_SERVICE=gtn-release
  GTN_CURRENT_PORT=5000
  GTN_ENV_DIR=/etc/gtn
  GTN_GIT_BRANCH=main
  GTN_GIT_REMOTE=origin
  GTN_GIT_URL=https://...

This script does not reload nginx and does not drain/stop the current release.
EOF
  exit 0
fi

if ! [[ "$SERVICE_NAME" =~ ^[A-Za-z0-9][A-Za-z0-9_.@-]*$ ]]; then
  echo "Invalid GTN_NEXT_SERVICE: $SERVICE_NAME" >&2
  exit 2
fi
if ! [[ "$CURRENT_SERVICE" =~ ^[A-Za-z0-9][A-Za-z0-9_.@-]*$ ]]; then
  echo "Invalid GTN_CURRENT_SERVICE: $CURRENT_SERVICE" >&2
  exit 2
fi
while [[ "$SERVICE_NAME" == *.service ]]; do
  SERVICE_NAME="${SERVICE_NAME%.service}"
done
while [[ "$CURRENT_SERVICE" == *.service ]]; do
  CURRENT_SERVICE="${CURRENT_SERVICE%.service}"
done
if [[ "$SERVICE_NAME" == "$CURRENT_SERVICE" ]]; then
  echo "Next service must differ from current service: $SERVICE_NAME" >&2
  exit 2
fi
if ! [[ "$PORT" =~ ^[1-9][0-9]*$ ]] || (( PORT < 1 || PORT > 65535 )); then
  echo "Invalid GTN_NEXT_PORT: $PORT" >&2
  exit 2
fi
if ! [[ "$CURRENT_PORT" =~ ^[1-9][0-9]*$ ]] || (( CURRENT_PORT < 1 || CURRENT_PORT > 65535 )); then
  echo "Invalid GTN_CURRENT_PORT: $CURRENT_PORT" >&2
  exit 2
fi
if (( PORT == CURRENT_PORT )); then
  echo "Next port must differ from current port: $PORT" >&2
  exit 2
fi
if ! [[ "$INSTANCE" =~ ^[A-Za-z0-9_.-]+$ ]]; then
  echo "Invalid GTN_INSTANCE: $INSTANCE" >&2
  exit 2
fi
if ! [[ "$REMOTE_NAME" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
  echo "Invalid GTN_GIT_REMOTE: $REMOTE_NAME" >&2
  exit 2
fi
if ! git check-ref-format "refs/heads/$BRANCH" >/dev/null 2>&1; then
  echo "Invalid GTN_GIT_BRANCH: $BRANCH" >&2
  exit 2
fi

for path_value in "$RELEASE_DIR" "$NEXT_DIR" "$ENV_DIR"; do
  if ! [[ "$path_value" =~ ^/[A-Za-z0-9_./@+-]+$ ]]; then
    echo "Deployment paths must be absolute and contain only safe characters: $path_value" >&2
    exit 2
  fi
done
RELEASE_DIR="$(realpath -m -- "$RELEASE_DIR")"
NEXT_DIR="$(realpath -m -- "$NEXT_DIR")"
ENV_DIR="$(realpath -m -- "$ENV_DIR")"
for path_value in "$RELEASE_DIR" "$NEXT_DIR" "$ENV_DIR"; do
  if ! [[ "$path_value" =~ ^/[A-Za-z0-9_./@+-]+$ ]]; then
    echo "Canonical deployment paths must contain only safe characters: $path_value" >&2
    exit 2
  fi
done
paths_overlap() {
  local left="$1"
  local right="$2"
  [[ "$left" == "$right" || "$left" == "$right"/* || "$right" == "$left"/* ]]
}
for path_value in "$RELEASE_DIR" "$NEXT_DIR" "$ENV_DIR"; do
  if [[ "$path_value" == "/" ]]; then
    echo "Deployment directories must not be the filesystem root." >&2
    exit 2
  fi
done
if paths_overlap "$RELEASE_DIR" "$NEXT_DIR" \
  || paths_overlap "$RELEASE_DIR" "$ENV_DIR" \
  || paths_overlap "$NEXT_DIR" "$ENV_DIR"; then
  echo "Release, next, and environment directories must be separate, non-nested paths." >&2
  exit 2
fi

if [[ ! -e "$RELEASE_DIR/.git" \
  || ! -f "$RELEASE_DIR/app.py" \
  || ! -f "$RELEASE_DIR/requirements.txt" ]]; then
  echo "GTN_RELEASE_DIR is not a GTN git checkout: $RELEASE_DIR" >&2
  exit 1
fi

TARGET_MARKER="$NEXT_DIR/.gtn-blue-green-target"
if [[ -e "$NEXT_DIR" && ! -d "$NEXT_DIR" ]]; then
  echo "GTN_NEXT_DIR exists but is not a directory: $NEXT_DIR" >&2
  exit 1
fi
if [[ -d "$NEXT_DIR" \
  && -n "$(find "$NEXT_DIR" -mindepth 1 -maxdepth 1 -print -quit)" \
  && ( ! -f "$TARGET_MARKER" \
    || ! -e "$NEXT_DIR/.git" \
    || ! -f "$NEXT_DIR/app.py" \
    || ! -f "$NEXT_DIR/requirements.txt" ) ]]; then
  echo "Existing next directory is not a marked disposable GTN checkout: $NEXT_DIR" >&2
  exit 1
fi

SHARED_ENV_FILE="$ENV_DIR/shared.env"
RELEASE_ENV_FILE="$ENV_DIR/release.env"
AI_ENV_FILE="$ENV_DIR/ai.env"

INSTANCE_ENV_FILE="$ENV_DIR/${SERVICE_NAME}.env"
for required_env in "$SHARED_ENV_FILE" "$RELEASE_ENV_FILE" "$AI_ENV_FILE"; do
  if [[ ! -r "$required_env" ]]; then
    echo "Required environment file is not readable: $required_env" >&2
    exit 1
  fi
done

INSTANCE_ENV_TMP=""
UNIT_TMP=""
HEALTH_TMP_DIR=""
cleanup_prepare_tmp() {
  if [[ -n "$INSTANCE_ENV_TMP" && -e "$INSTANCE_ENV_TMP" ]]; then
    rm -f -- "$INSTANCE_ENV_TMP"
  fi
  if [[ -n "$UNIT_TMP" && -e "$UNIT_TMP" ]]; then
    rm -f -- "$UNIT_TMP"
  fi
  if [[ -n "$HEALTH_TMP_DIR" && -d "$HEALTH_TMP_DIR" ]]; then
    rm -rf -- "$HEALTH_TMP_DIR"
  fi
}
trap cleanup_prepare_tmp EXIT

# Keep the stable flock target in a root-only runtime directory.  A predictable
# file directly under /tmp could be replaced with a symlink before root opens it.
install -d -m 0700 -o root -g root /run/gtn-deploy
exec 9>/run/gtn-deploy/prepare-next.lock
if ! flock -n 9; then
  echo "Another prepare-next run is already active." >&2
  exit 1
fi

if [[ -z "$REMOTE_URL" ]]; then
  REMOTE_URL="$(git -C "$RELEASE_DIR" remote get-url "$REMOTE_NAME")"
fi

echo "Preparing GTN next instance"
echo "  repo:    $REMOTE_URL"
echo "  branch:  $BRANCH"
echo "  target:  $NEXT_DIR"
echo "  service: $SERVICE_NAME"
echo "  port:    $PORT"

if [[ ! -e "$NEXT_DIR/.git" ]]; then
  mkdir -p "$(dirname "$NEXT_DIR")"
  git clone --origin "$REMOTE_NAME" --branch "$BRANCH" -- "$REMOTE_URL" "$NEXT_DIR"
  if [[ ! -f "$NEXT_DIR/app.py" || ! -f "$NEXT_DIR/requirements.txt" ]]; then
    echo "Cloned repository is not a GTN checkout; refusing to mark it disposable." >&2
    exit 1
  fi
  install -m 0600 /dev/null "$TARGET_MARKER"
else
  if git -C "$NEXT_DIR" remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
    git -C "$NEXT_DIR" remote set-url "$REMOTE_NAME" "$REMOTE_URL"
  else
    git -C "$NEXT_DIR" remote add "$REMOTE_NAME" "$REMOTE_URL"
  fi
  git -C "$NEXT_DIR" fetch "$REMOTE_NAME" \
    "+refs/heads/${BRANCH}:refs/remotes/${REMOTE_NAME}/${BRANCH}"
  git -C "$NEXT_DIR" checkout -B "$BRANCH" "${REMOTE_NAME}/${BRANCH}"
  git -C "$NEXT_DIR" reset --hard "${REMOTE_NAME}/${BRANCH}"
  git -C "$NEXT_DIR" clean -fd -e venv -e .venv -e .gtn-blue-green-target
fi

SHA="$(git -C "$NEXT_DIR" rev-parse --short HEAD)"
VERSION="$SHA"
INSTANCE_ID="${INSTANCE}-${PORT}-${SHA}"

cd "$NEXT_DIR"
if [[ ! -d venv ]]; then
  python3 -m venv venv
fi
source venv/bin/activate
python -m pip install -q --upgrade pip
pip install -q -r requirements.txt
python -m py_compile app.py db.py game_engine.py game_engine_2v2.py game_engine_urf.py

INSTANCE_ENV_TMP="$(mktemp "$ENV_DIR/.${SERVICE_NAME}.env.XXXXXX")"
cat > "$INSTANCE_ENV_TMP" <<EOF
GTN_INSTANCE=${INSTANCE}
GTN_INSTANCE_ID=${INSTANCE_ID}
GTN_VERSION=${VERSION}
GTN_GIT_SHA=${SHA}
GTN_STATIC_VERSION=${SHA}
GTN_BIND_HOST=127.0.0.1
GTN_PORT=${PORT}
GTN_DRAIN_FILE=/tmp/gtn-${INSTANCE_ID}.drain
GTN_SYSTEMD_SERVICE=${SERVICE_NAME}
GTN_DB_MAINTENANCE_ENABLED=0
EOF
chmod 0640 "$INSTANCE_ENV_TMP"
chown root:root "$INSTANCE_ENV_TMP"

UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
UNIT_TMP="$(mktemp "/etc/systemd/system/.${SERVICE_NAME}.service.XXXXXX")"
cat > "$UNIT_TMP" <<EOF
[Unit]
Description=Garden of Thorn next instance
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${NEXT_DIR}
EnvironmentFile=${SHARED_ENV_FILE}
EnvironmentFile=${RELEASE_ENV_FILE}
EnvironmentFile=${AI_ENV_FILE}
EnvironmentFile=${INSTANCE_ENV_FILE}
ExecStart=${NEXT_DIR}/venv/bin/python ${NEXT_DIR}/app.py
Restart=always
RestartSec=3
KillSignal=SIGINT
TimeoutStopSec=25

[Install]
WantedBy=multi-user.target
EOF
chmod 0644 "$UNIT_TMP"
chown root:root "$UNIT_TMP"

# Publish only after dependencies and compilation have succeeded.  Both moves
# stay within their destination directories, so readers never see partial files.
mv -f -- "$INSTANCE_ENV_TMP" "$INSTANCE_ENV_FILE"
INSTANCE_ENV_TMP=""
mv -f -- "$UNIT_TMP" "$UNIT_FILE"
UNIT_TMP=""

systemctl daemon-reload
systemctl restart "$SERVICE_NAME"

echo "Waiting for health check..."
HEALTH_TMP_DIR="$(mktemp -d /tmp/gtn-prepare-health.XXXXXX)"
chmod 0700 "$HEALTH_TMP_DIR"
HEALTH_JSON="$HEALTH_TMP_DIR/health.json"
FULL_HEALTH_JSON="$HEALTH_TMP_DIR/health-full.json"
AI_STATUS_JSON="$HEALTH_TMP_DIR/ai-status.json"
for i in $(seq 1 30); do
  if curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/api/healthz" >"$HEALTH_JSON" \
    && python3 - "$HEALTH_JSON" "$INSTANCE_ID" "$SHA" "$PORT" <<'PY'
import json
import sys

path, instance_id, sha, port = sys.argv[1:]
with open(path, encoding='utf-8') as fh:
    payload = json.load(fh)
valid = (
    payload.get('success') is True
    and payload.get('instance_id') == instance_id
    and payload.get('version') == sha
    and payload.get('git_sha') == sha
    and int(payload.get('port') or 0) == int(port)
    and payload.get('draining') is False
)
raise SystemExit(0 if valid else 1)
PY
  then
    echo "Next instance is healthy:"
    cat "$HEALTH_JSON"
    echo
    break
  fi
  sleep 1
  if [[ "$i" == "30" ]]; then
    echo "Next instance did not become healthy. Recent logs:" >&2
    journalctl -u "$SERVICE_NAME" --since "-2 min" --no-pager -l | tail -120 >&2
    exit 1
  fi
done

curl -fsS --max-time 5 "http://127.0.0.1:${PORT}/api/health/full" >"$FULL_HEALTH_JSON"
python3 - "$FULL_HEALTH_JSON" "$SHA" <<'PY'
import json
import sys

with open(sys.argv[1], encoding='utf-8') as fh:
    payload = json.load(fh)
valid = (
    payload.get('success') is True
    and payload.get('db_ok') is True
    and payload.get('socket_ok') is True
    and payload.get('git_sha') == sys.argv[2]
)
raise SystemExit(0 if valid else 1)
PY

curl -fsS --max-time 5 "http://127.0.0.1:${PORT}/api/ai-1v1/status" >"$AI_STATUS_JSON"
python3 - "$AI_STATUS_JSON" <<'PY'
import json
import sys

with open(sys.argv[1], encoding='utf-8') as fh:
    payload = json.load(fh)
valid = (
    payload.get('success') is True
    and payload.get('enabled') is True
    and int(payload.get('capacity') or 0) > 0
)
raise SystemExit(0 if valid else 1)
PY

cat <<EOF

Prepared next instance.

No nginx switch was performed.
To inspect:
  systemctl status ${SERVICE_NAME} --no-pager -l
  curl -fsS http://127.0.0.1:${PORT}/api/health/full

To switch new public traffic after manual verification:
  /usr/local/bin/gtn-switch-next.sh
  # or: ${NEXT_DIR}/scripts/blue_green_switch_nginx.sh ${PORT} ${NEXT_DIR}
  systemctl reload nginx

Then mark the old release instance draining from its console:
  drain on

Rollback before nginx reload:
  systemctl stop ${SERVICE_NAME}

Rollback after nginx reload:
  /opt/gtn-release/scripts/blue_green_switch_nginx.sh 5000 /opt/gtn-release
  systemctl reload nginx
  systemctl stop ${SERVICE_NAME}
EOF
