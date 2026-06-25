#!/usr/bin/env bash
set -u

SERVICE="${1:-gtn-release-next}"
PORT="${2:-5002}"
DEPLOY_DIR="${3:-/opt/gtn-next}"

LOG_FILE="${GTN_HEALTHCHECK_LOG:-/var/log/gtn-healthcheck.log}"
STATE_DIR="${GTN_HEALTHCHECK_STATE_DIR:-/run/gtn-healthcheck}"
SNAPSHOT_DIR="${GTN_HEALTHCHECK_SNAPSHOT_DIR:-/root/gtn-freeze-dumps}"
LOCK_FILE="/tmp/${SERVICE}-healthcheck.lock"
FAIL_FILE="${STATE_DIR}/${SERVICE}.fail"
RESTART_AFTER="${GTN_HEALTHCHECK_RESTART_AFTER:-2}"
HTTP_TIMEOUT="${GTN_HEALTHCHECK_HTTP_TIMEOUT:-4}"

mkdir -p "$STATE_DIR"

log() {
    printf '%s [%s] %s\n' "$(date '+%F %T')" "$SERVICE" "$*" >> "$LOG_FILE"
}

is_deploy_active() {
    pgrep -f "gtn-update-instance.sh ${DEPLOY_DIR}|git .*fetch|pip install" >/dev/null 2>&1
}

snapshot() {
    local reason="$1"
    local ts file pid
    ts="$(date '+%Y%m%d-%H%M%S')"
    mkdir -p "$SNAPSHOT_DIR" 2>/dev/null || true
    file="${SNAPSHOT_DIR}/${SERVICE}-${ts}.log"
    pid="$(systemctl show -p MainPID --value "$SERVICE" 2>/dev/null || true)"
    {
        echo "===== reason ====="
        echo "$reason"
        echo "===== time ====="
        date
        echo "===== service ====="
        systemctl status "$SERVICE" --no-pager -l || true
        echo "===== process ====="
        if [ -n "$pid" ] && [ "$pid" != "0" ]; then
            ps -p "$pid" -o pid,ppid,%cpu,%mem,rss,vsz,etime,stat,wchan:30,cmd || true
            echo "===== process stack ====="
            cat "/proc/${pid}/stack" 2>/dev/null || true
        else
            echo "no main pid"
        fi
        echo "===== ports ====="
        ss -ltnp | grep -E ':80|:443|:5000|:5001|:5002' || true
        echo "===== established connection count ====="
        ss -tan state established | grep -E ':443|:5000|:5001|:5002' | wc -l || true
        echo "===== local health ====="
        curl -m "$HTTP_TIMEOUT" -i "http://127.0.0.1:${PORT}/api/health/full" || true
        echo
        echo "===== local socket ====="
        curl -m "$HTTP_TIMEOUT" -i "http://127.0.0.1:${PORT}/socket.io/?EIO=4&transport=polling&t=$(date +%s%N)" || true
        echo
        echo "===== recent app logs ====="
        journalctl -u "$SERVICE" --since "-15 min" --no-pager -l | tail -260 || true
        echo "===== recent nginx errors ====="
        tail -n 180 /var/log/nginx/error.log 2>/dev/null || true
        echo "===== recent nginx access 5xx/499 ====="
        tail -n 600 /var/log/nginx/access.log 2>/dev/null | grep -E ' 499 | 5[0-9][0-9] ' | tail -120 || true
    } > "$file" 2>&1
    log "snapshot saved file=$file reason=$reason"
}

fail_once() {
    local reason="$1"
    local count
    count=0
    if [ -f "$FAIL_FILE" ]; then
        count="$(cat "$FAIL_FILE" 2>/dev/null || echo 0)"
    fi
    count=$((count + 1))
    echo "$count" > "$FAIL_FILE"
    log "failed count=$count reason=$reason"
    if [ "$count" -ge "$RESTART_AFTER" ]; then
        snapshot "$reason"
        log "restarting after $count consecutive failures"
        systemctl restart "$SERVICE" || log "restart command failed"
        echo 0 > "$FAIL_FILE"
    fi
    exit 1
}

pass_once() {
    echo 0 > "$FAIL_FILE"
    log "ok"
    exit 0
}

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "skip: previous healthcheck still running"
    exit 0
fi

if is_deploy_active; then
    log "skip: deploy process active"
    exit 0
fi

systemctl is-active --quiet "$SERVICE" || fail_once "service_inactive"

if ! ss -ltn "( sport = :$PORT )" | grep -q ":$PORT"; then
    fail_once "port_${PORT}_not_listening"
fi

home_status="$(curl -m "$HTTP_TIMEOUT" -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/" || true)"
case "$home_status" in
    200|301|302) ;;
    *) fail_once "homepage_bad_status_${home_status:-curl_failed}" ;;
esac

socket_status="$(curl -m "$HTTP_TIMEOUT" -s -o /tmp/${SERVICE}-socket-health.$$ -w '%{http_code}' "http://127.0.0.1:${PORT}/socket.io/?EIO=4&transport=polling&t=$(date +%s%N)" || true)"
if [ "$socket_status" != "200" ] || ! grep -q '"sid"' "/tmp/${SERVICE}-socket-health.$$" 2>/dev/null; then
    rm -f "/tmp/${SERVICE}-socket-health.$$"
    fail_once "socket_polling_bad_status_${socket_status:-curl_failed}"
fi
rm -f "/tmp/${SERVICE}-socket-health.$$"

health_json="$(curl -m "$HTTP_TIMEOUT" -s "http://127.0.0.1:${PORT}/api/health/full" || true)"
if [ -z "$health_json" ]; then
    fail_once "health_empty"
fi

health_reason="$(HEALTH_JSON="$health_json" python3 - <<'PY'
import json
import os
import sys

try:
    data = json.loads(os.environ.get("HEALTH_JSON") or "")
except Exception as exc:
    print(f"invalid_json:{exc}")
    sys.exit(2)

if data.get("success") is False:
    print("success_false")
    sys.exit(2)
if data.get("db_ok") is False:
    print("db_not_ok")
    sys.exit(2)
if data.get("socket_ok") is False:
    print("socket_not_ok")
    sys.exit(2)
if data.get("lobby_ok") is False:
    print("lobby_not_ok")
    sys.exit(2)
if data.get("global_lock_busy") and float(data.get("global_lock_held_seconds") or 0) > 60:
    print("global_lock_stuck")
    sys.exit(2)

print("ok")
PY
)"
health_result="$?"
if [ "$health_result" != "0" ]; then
    fail_once "health_full_bad:${health_reason:-unknown}"
fi

pass_once
