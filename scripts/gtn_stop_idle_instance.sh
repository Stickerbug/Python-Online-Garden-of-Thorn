#!/usr/bin/env bash
set -euo pipefail

# Stop a previous GTN instance after it has no players, rooms, or lobby users.
# Intended for blue-green deployment after nginx has switched new traffic away.

PORT="${1:-}"
SERVICE="${2:-}"
INTERVAL="${GTN_IDLE_STOP_INTERVAL:-30}"
MAX_SECONDS="${GTN_IDLE_STOP_MAX_SECONDS:-21600}"
LOG_FILE="${GTN_IDLE_STOP_LOG:-/var/log/gtn-idle-stop.log}"
LOCK_FILE="/tmp/gtn-idle-stop-${PORT}-${SERVICE}.lock"

if [[ -z "$PORT" || -z "$SERVICE" ]]; then
  echo "Usage: gtn_stop_idle_instance.sh PORT SYSTEMD_SERVICE" >&2
  exit 2
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date '+%F %T') $SERVICE/$PORT idle-stop monitor already running" >> "$LOG_FILE"
  exit 0
fi

log() { echo "$(date '+%F %T') $*" >> "$LOG_FILE"; }

log "start monitor service=$SERVICE port=$PORT interval=${INTERVAL}s max=${MAX_SECONDS}s"
start_ts=$(date +%s)

while true; do
  if ! systemctl is-active --quiet "$SERVICE"; then
    log "service already inactive service=$SERVICE port=$PORT"
    exit 0
  fi

  json=$(curl -fsS --max-time 5 "http://127.0.0.1:${PORT}/api/health/full" 2>/dev/null || true)
  if [[ -z "$json" ]]; then
    elapsed=$(( $(date +%s) - start_ts ))
    log "health unavailable service=$SERVICE port=$PORT elapsed=${elapsed}s"
    if (( elapsed >= MAX_SECONDS )); then
      log "max wait reached with unavailable health; leaving service running service=$SERVICE port=$PORT"
      exit 1
    fi
    sleep "$INTERVAL"
    continue
  fi

  read -r players rooms lobby drain_file <<<"$(python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(int(d.get("player_count") or 0), int(d.get("room_count") or 0), int(d.get("lobby_player_count") or 0), d.get("drain_file") or "")' <<<"$json")"
  if [[ -n "$drain_file" ]]; then
    touch "$drain_file" 2>/dev/null || true
  fi

  log "check service=$SERVICE port=$PORT players=$players rooms=$rooms lobby=$lobby"
  if (( players == 0 && rooms == 0 && lobby == 0 )); then
    log "stopping idle service=$SERVICE port=$PORT"
    systemctl stop "$SERVICE"
    log "stopped service=$SERVICE port=$PORT"
    exit 0
  fi

  elapsed=$(( $(date +%s) - start_ts ))
  if (( elapsed >= MAX_SECONDS )); then
    log "max wait reached; leaving service running service=$SERVICE port=$PORT players=$players rooms=$rooms lobby=$lobby"
    exit 1
  fi
  sleep "$INTERVAL"
done
