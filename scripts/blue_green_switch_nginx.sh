#!/usr/bin/env bash
set -euo pipefail

# Switch only the release server block in the GTN nginx config to a target
# backend port and static root.  The script writes a timestamped backup and runs
# nginx -t, but deliberately does not reload nginx.

PORT="${1:-}"
ROOT_DIR="${2:-}"
CONF="${3:-/etc/nginx/sites-available/gtn}"

if [[ -z "$PORT" || -z "$ROOT_DIR" ]]; then
  echo "Usage: $0 <port> <root_dir> [nginx_conf]" >&2
  echo "Example: $0 5002 /opt/gtn-next" >&2
  exit 2
fi
if [[ ! "$PORT" =~ ^[0-9]+$ ]]; then
  echo "Invalid port: $PORT" >&2
  exit 2
fi
if [[ ! -d "$ROOT_DIR" ]]; then
  echo "Root directory does not exist: $ROOT_DIR" >&2
  exit 2
fi
if [[ ! -f "$CONF" ]]; then
  echo "Nginx config does not exist: $CONF" >&2
  exit 2
fi

BACKUP="${CONF}.bak-bluegreen-$(date +%F-%H%M%S)"
cp "$CONF" "$BACKUP"

python3 - "$CONF" "$PORT" "$ROOT_DIR" <<'PY'
import re
import sys
from pathlib import Path

conf = Path(sys.argv[1])
port = sys.argv[2]
root = sys.argv[3].rstrip("/")
text = conf.read_text(encoding="utf-8")
marker = "# =========================\n# Garden of Thorn Beta"
if marker in text:
    release, rest = text.split(marker, 1)
    rest = marker + rest
else:
    release, rest = text, ""

if "map $cookie_gtn_route_port $gtn_release_backend" in release:
    release = re.sub(
        r"(map\s+\$cookie_gtn_route_port\s+\$gtn_release_backend\s*\{[^{}]*?default\s+)127\.0\.0\.1:\d+(\s*;)",
        rf"\g<1>127.0.0.1:{port}\2",
        release,
        count=1,
        flags=re.S,
    )
else:
    release = re.sub(
        r"proxy_pass http://127\.0\.0\.1:\d+(/socket\.io/)?;",
        lambda m: f"proxy_pass http://127.0.0.1:{port}{m.group(1) or ''};",
        release,
    )
release = release.replace("alias /opt/gtn-release/static/;", f"alias {root}/static/;")
release = release.replace("alias /opt/gtn-release/static/fonts/;", f"alias {root}/static/fonts/;")
release = release.replace("alias /opt/gtn-release/static/assets/icons/favicon.ico;", f"alias {root}/static/assets/icons/favicon.ico;")
conf.write_text(release + rest, encoding="utf-8")
PY

nginx -t
cat <<EOF
Nginx release origin switched in config only:
  port: $PORT
  static root: $ROOT_DIR/static
  backup: $BACKUP

To apply:
  systemctl reload nginx

To rollback config:
  cp "$BACKUP" "$CONF"
  nginx -t && systemctl reload nginx
EOF
