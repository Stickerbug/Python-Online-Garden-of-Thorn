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
INSTANCE="${GTN_INSTANCE:-release}"
BRANCH="${GTN_GIT_BRANCH:-main}"
REMOTE_NAME="${GTN_GIT_REMOTE:-origin}"
LOCK_FILE="${GTN_PREPARE_LOCK:-/tmp/gtn-prepare-next.lock}"
REMOTE_URL="${GTN_GIT_URL:-}"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<EOF
Usage:
  gtn_prepare_next.sh

Environment overrides:
  GTN_RELEASE_DIR=/opt/gtn-release
  GTN_NEXT_DIR=/opt/gtn-next
  GTN_NEXT_SERVICE=gtn-release-next
  GTN_NEXT_PORT=5002
  GTN_GIT_BRANCH=main
  GTN_GIT_REMOTE=origin
  GTN_GIT_URL=https://...

This script does not reload nginx and does not drain/stop the current release.
EOF
  exit 0
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "Another prepare-next run is already active: $LOCK_FILE" >&2
  exit 1
fi

if [[ -z "$REMOTE_URL" ]]; then
  if [[ ! -d "$RELEASE_DIR/.git" ]]; then
    echo "Cannot discover git remote: $RELEASE_DIR is not a git repo." >&2
    exit 1
  fi
  REMOTE_URL="$(git -C "$RELEASE_DIR" remote get-url "$REMOTE_NAME")"
fi

echo "Preparing GTN next instance"
echo "  repo:    $REMOTE_URL"
echo "  branch:  $BRANCH"
echo "  target:  $NEXT_DIR"
echo "  service: $SERVICE_NAME"
echo "  port:    $PORT"

if [[ -e "$NEXT_DIR" && ! -d "$NEXT_DIR/.git" ]]; then
  echo "$NEXT_DIR exists but is not a git checkout. Refusing to overwrite." >&2
  exit 1
fi

if [[ ! -d "$NEXT_DIR/.git" ]]; then
  mkdir -p "$(dirname "$NEXT_DIR")"
  git clone --branch "$BRANCH" "$REMOTE_URL" "$NEXT_DIR"
else
  git -C "$NEXT_DIR" remote set-url origin "$REMOTE_URL" || true
  git -C "$NEXT_DIR" fetch origin "$BRANCH"
  git -C "$NEXT_DIR" checkout -B "$BRANCH" "origin/$BRANCH"
  git -C "$NEXT_DIR" reset --hard "origin/$BRANCH"
  git -C "$NEXT_DIR" clean -fd -e venv -e .venv
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

if [[ -d "$RELEASE_DIR/scripts" ]]; then
  mkdir -p "$NEXT_DIR/scripts"
  for helper in blue_green_status.sh blue_green_switch_nginx.sh BLUE_GREEN_DEPLOY.md gtn-blue-green.service.template nginx-blue-green-gtn.conf.template; do
    if [[ -f "$RELEASE_DIR/scripts/$helper" ]]; then
      cp "$RELEASE_DIR/scripts/$helper" "$NEXT_DIR/scripts/$helper"
      [[ "$helper" == *.sh ]] && chmod +x "$NEXT_DIR/scripts/$helper"
    fi
  done
fi

cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Garden of Thorn next instance
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${NEXT_DIR}
Environment=GTN_INSTANCE=${INSTANCE}
Environment=GTN_INSTANCE_ID=${INSTANCE_ID}
Environment=GTN_VERSION=${VERSION}
Environment=GTN_GIT_SHA=${SHA}
Environment=GTN_STATIC_VERSION=${SHA}
Environment=GTN_BIND_HOST=127.0.0.1
Environment=GTN_PORT=${PORT}
Environment=GTN_DRAIN_FILE=/tmp/gtn-${INSTANCE_ID}.drain
Environment=GTN_SYSTEMD_SERVICE=${SERVICE_NAME}
Environment=GTN_DB_MAINTENANCE_ENABLED=0
ExecStart=${NEXT_DIR}/venv/bin/python ${NEXT_DIR}/app.py
Restart=always
RestartSec=3
KillSignal=SIGINT
TimeoutStopSec=25

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl restart "$SERVICE_NAME"

echo "Waiting for health check..."
for i in $(seq 1 30); do
  if curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/api/healthz" >/tmp/gtn-next-health.json; then
    echo "Next instance is healthy:"
    cat /tmp/gtn-next-health.json
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
