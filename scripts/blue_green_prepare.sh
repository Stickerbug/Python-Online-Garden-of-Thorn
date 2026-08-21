#!/usr/bin/env bash
set -euo pipefail

# Prepare a new GTN instance directory without touching the currently running
# service.  This script is intentionally conservative: it copies code, installs
# dependencies if a venv exists or can be created, and atomically writes the
# non-secret instance override environment.  Nginx switching and systemd
# restart are left to the operator.

SOURCE_DIR="${1:-/opt/gtn-release}"
TARGET_DIR="${2:-/opt/gtn-next}"
PORT="${3:-5002}"
INSTANCE="${4:-release}"
SERVICE_NAME="${GTN_NEXT_SERVICE:-gtn-release-next}"
CURRENT_SERVICE="${GTN_CURRENT_SERVICE:-gtn-release}"
CURRENT_PORT="${GTN_CURRENT_PORT:-5000}"
ENV_DIR="${GTN_ENV_DIR:-/etc/gtn}"

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
  echo "Invalid port: $PORT" >&2
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
  echo "Invalid instance name: $INSTANCE" >&2
  exit 2
fi

for path_value in "$SOURCE_DIR" "$TARGET_DIR" "$ENV_DIR"; do
  if ! [[ "$path_value" =~ ^/[A-Za-z0-9_./@+-]+$ ]]; then
    echo "Deployment paths must be absolute and contain only safe characters: $path_value" >&2
    exit 2
  fi
done
SOURCE_DIR="$(realpath -m -- "$SOURCE_DIR")"
TARGET_DIR="$(realpath -m -- "$TARGET_DIR")"
ENV_DIR="$(realpath -m -- "$ENV_DIR")"
for path_value in "$SOURCE_DIR" "$TARGET_DIR" "$ENV_DIR"; do
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
for path_value in "$SOURCE_DIR" "$TARGET_DIR" "$ENV_DIR"; do
  if [[ "$path_value" == "/" ]]; then
    echo "Deployment directories must not be the filesystem root." >&2
    exit 2
  fi
done
if paths_overlap "$SOURCE_DIR" "$TARGET_DIR" \
  || paths_overlap "$SOURCE_DIR" "$ENV_DIR" \
  || paths_overlap "$TARGET_DIR" "$ENV_DIR"; then
  echo "Source, target, and environment directories must be separate, non-nested paths." >&2
  exit 1
fi

if [[ ! -e "$SOURCE_DIR/.git" \
  || ! -f "$SOURCE_DIR/app.py" \
  || ! -f "$SOURCE_DIR/requirements.txt" ]]; then
  echo "Source is not a GTN git checkout: $SOURCE_DIR" >&2
  exit 1
fi
if [[ -d "$TARGET_DIR" \
  && -n "$(find "$TARGET_DIR" -mindepth 1 -maxdepth 1 -print -quit)" \
  && ! -f "$TARGET_DIR/.gtn-blue-green-target" ]]; then
  echo "Target is non-empty but is not marked as a disposable GTN next instance: $TARGET_DIR" >&2
  exit 1
fi

SHARED_ENV_FILE="$ENV_DIR/shared.env"
RELEASE_ENV_FILE="$ENV_DIR/release.env"
AI_ENV_FILE="$ENV_DIR/ai.env"
for required_env in "$SHARED_ENV_FILE" "$RELEASE_ENV_FILE" "$AI_ENV_FILE"; do
  if [[ ! -r "$required_env" ]]; then
    echo "Required environment file is not readable: $required_env" >&2
    exit 1
  fi
done

echo "Preparing GTN instance"
echo "  source: $SOURCE_DIR"
echo "  target: $TARGET_DIR"
echo "  port:   $PORT"

mkdir -p "$TARGET_DIR"
install -m 0600 /dev/null "$TARGET_DIR/.gtn-blue-green-target"

rsync -a --delete \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'venv' \
  --exclude '.venv' \
  --exclude '.gtn-blue-green-target' \
  "$SOURCE_DIR"/ "$TARGET_DIR"/

cd "$TARGET_DIR"

if [[ ! -d venv ]]; then
  python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt
python -m py_compile app.py db.py game_engine.py game_engine_2v2.py game_engine_urf.py

GIT_SHA=""
if command -v git >/dev/null 2>&1 \
  && git -C "$SOURCE_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_SHA="$(git -C "$SOURCE_DIR" rev-parse --short HEAD 2>/dev/null || true)"
fi

STATIC_VERSION="${GIT_SHA:-$(date +%Y%m%d%H%M%S)}"
INSTANCE_ID="${INSTANCE}-${PORT}-${STATIC_VERSION}"
INSTANCE_ENV_FILE="$ENV_DIR/${SERVICE_NAME}.env"
INSTANCE_ENV_TMP="$(mktemp "$ENV_DIR/.${SERVICE_NAME}.env.XXXXXX")"
cleanup_instance_env_tmp() {
  if [[ -n "${INSTANCE_ENV_TMP:-}" && -e "$INSTANCE_ENV_TMP" ]]; then
    rm -f -- "$INSTANCE_ENV_TMP"
  fi
}
trap cleanup_instance_env_tmp EXIT
cat > "$INSTANCE_ENV_TMP" <<EOF
GTN_INSTANCE=${INSTANCE}
GTN_INSTANCE_ID=${INSTANCE_ID}
GTN_VERSION=${STATIC_VERSION}
GTN_GIT_SHA=${GIT_SHA}
GTN_STATIC_VERSION=${STATIC_VERSION}
GTN_BIND_HOST=127.0.0.1
GTN_PORT=${PORT}
GTN_DRAIN_FILE=/tmp/gtn-${INSTANCE_ID}.drain
GTN_SYSTEMD_SERVICE=${SERVICE_NAME}
GTN_DB_MAINTENANCE_ENABLED=0
EOF
chmod 0640 "$INSTANCE_ENV_TMP"
chown root:root "$INSTANCE_ENV_TMP"
mv -f -- "$INSTANCE_ENV_TMP" "$INSTANCE_ENV_FILE"
INSTANCE_ENV_TMP=""
trap - EXIT

cat <<EOF

Prepared.

Instance overrides were written to:
  $INSTANCE_ENV_FILE

Start this instance only through a systemd unit that loads EnvironmentFile in
this order (later files override earlier files):
  $SHARED_ENV_FILE
  $RELEASE_ENV_FILE
  $AI_ENV_FILE
  $INSTANCE_ENV_FILE

The default scripts/gtn-blue-green.service.template uses the default service
name gtn-release-next. If GTN_NEXT_SERVICE was overridden, update its final
EnvironmentFile path and unit name to match before starting it.

After Nginx points new users to this port, mark the old instance draining from
the old server console:
  drain on

EOF
