#!/usr/bin/env bash
set -euo pipefail

# Validate next instance and switch nginx config to it.  By default this script
# does not reload nginx.  Use --apply to reload after nginx -t succeeds.

NEXT_PORT="${GTN_NEXT_PORT:-5002}"
NEXT_DIR="${GTN_NEXT_DIR:-/opt/gtn-next}"
RELEASE_DIR="${GTN_RELEASE_DIR:-/opt/gtn-release}"
APPLY=0
OLD_PORT="${GTN_OLD_PORT:-5000}"
OLD_SERVICE="${GTN_OLD_SERVICE:-gtn-release}"

for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=1 ;;
    --port=*) NEXT_PORT="${arg#*=}" ;;
    --next-dir=*) NEXT_DIR="${arg#*=}" ;;
    --release-dir=*) RELEASE_DIR="${arg#*=}" ;;
    --old-port=*) OLD_PORT="${arg#*=}" ;;
    --old-service=*) OLD_SERVICE="${arg#*=}" ;;
    -h|--help)
      cat <<EOF
Usage:
  gtn_switch_next.sh [--apply] [--port=5002] [--next-dir=/opt/gtn-next]

Without --apply, nginx config is changed and validated but not reloaded.
EOF
      exit 0
      ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

if [[ ! -d "$NEXT_DIR" ]]; then
  echo "Next directory does not exist: $NEXT_DIR" >&2
  exit 1
fi

echo "Checking next instance health..."
curl -fsS --max-time 5 "http://127.0.0.1:${NEXT_PORT}/api/healthz"
echo

SWITCH_SCRIPT="$NEXT_DIR/scripts/blue_green_switch_nginx.sh"
if [[ ! -x "$SWITCH_SCRIPT" ]]; then
  SWITCH_SCRIPT="$RELEASE_DIR/scripts/blue_green_switch_nginx.sh"
fi
if [[ ! -x "$SWITCH_SCRIPT" ]]; then
  echo "Cannot find blue_green_switch_nginx.sh in next or release scripts." >&2
  exit 1
fi

"$SWITCH_SCRIPT" "$NEXT_PORT" "$NEXT_DIR"

if [[ "$APPLY" == "1" ]]; then
  systemctl reload nginx
  echo "Nginx reloaded. Public release traffic should now target $NEXT_PORT."
  if [[ -x /usr/local/bin/gtn-stop-idle-instance.sh ]]; then
    echo "Starting idle-stop monitor for old instance $OLD_SERVICE on port $OLD_PORT."
    nohup /usr/local/bin/gtn-stop-idle-instance.sh "$OLD_PORT" "$OLD_SERVICE" >/var/log/gtn-idle-stop-launch.log 2>&1 &
  else
    echo "Warning: /usr/local/bin/gtn-stop-idle-instance.sh not found; old instance will not be auto-stopped." >&2
  fi
else
  echo "Nginx was not reloaded. Run this to apply:"
  echo "  systemctl reload nginx"
fi
