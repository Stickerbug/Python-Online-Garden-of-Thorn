#!/usr/bin/env bash
set -euo pipefail

# Prepare a new GTN instance directory without touching the currently running
# service.  This script is intentionally conservative: it copies code, installs
# dependencies if a venv exists or can be created, and prints the environment
# needed for the new service.  Nginx switching and systemd restart are left to
# the operator.

SOURCE_DIR="${1:-/opt/gtn-release}"
TARGET_DIR="${2:-/opt/gtn-next}"
PORT="${3:-5002}"
INSTANCE="${4:-release}"

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Source directory does not exist: $SOURCE_DIR" >&2
  exit 1
fi

if [[ "$SOURCE_DIR" == "$TARGET_DIR" ]]; then
  echo "Source and target directories must be different." >&2
  exit 1
fi

echo "Preparing GTN instance"
echo "  source: $SOURCE_DIR"
echo "  target: $TARGET_DIR"
echo "  port:   $PORT"

mkdir -p "$TARGET_DIR"

rsync -a --delete \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'venv' \
  --exclude '.venv' \
  "$SOURCE_DIR"/ "$TARGET_DIR"/

cd "$TARGET_DIR"

if [[ ! -d venv ]]; then
  python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt
python -m py_compile app.py db.py game_engine.py game_engine_2v2.py game_engine_urf.py

GIT_SHA=""
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || true)"
fi

STATIC_VERSION="${GIT_SHA:-$(date +%Y%m%d%H%M%S)}"
INSTANCE_ID="${INSTANCE}-${PORT}-${STATIC_VERSION}"

cat <<EOF

Prepared.

Suggested systemd environment for the new instance:
  GTN_INSTANCE=$INSTANCE
  GTN_INSTANCE_ID=$INSTANCE_ID
  GTN_VERSION=$STATIC_VERSION
  GTN_GIT_SHA=$GIT_SHA
  GTN_STATIC_VERSION=$STATIC_VERSION
  GTN_BIND_HOST=127.0.0.1
  GTN_PORT=$PORT
  GTN_DRAIN_FILE=/tmp/gtn-$INSTANCE_ID.drain
  GTN_DB_MAINTENANCE_ENABLED=0

Suggested manual start command for verification:
  cd "$TARGET_DIR"
  GTN_INSTANCE=$INSTANCE GTN_INSTANCE_ID=$INSTANCE_ID GTN_VERSION=$STATIC_VERSION GTN_GIT_SHA=$GIT_SHA GTN_STATIC_VERSION=$STATIC_VERSION GTN_BIND_HOST=127.0.0.1 GTN_PORT=$PORT GTN_DB_MAINTENANCE_ENABLED=0 ./venv/bin/python app.py

After Nginx points new users to this port, mark the old instance draining from
the old server console:
  drain on

EOF
