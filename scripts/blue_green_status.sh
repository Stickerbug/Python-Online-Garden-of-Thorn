#!/usr/bin/env bash
set -euo pipefail

# Print lightweight health information for one or more local GTN ports.
# Usage:
#   scripts/blue_green_status.sh 5000 5002

if [[ "$#" -eq 0 ]]; then
  set -- 5000
fi

for port in "$@"; do
  url="http://127.0.0.1:${port}/api/healthz"
  echo "===== $url ====="
  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 3 "$url" || {
      echo "unreachable"
      continue
    }
    echo
  else
    python3 - "$url" <<'PY'
import json
import sys
import urllib.request

url = sys.argv[1]
try:
    with urllib.request.urlopen(url, timeout=3) as resp:
        print(resp.read().decode("utf-8"))
except Exception as exc:
    print(f"unreachable: {exc}")
PY
  fi
done
