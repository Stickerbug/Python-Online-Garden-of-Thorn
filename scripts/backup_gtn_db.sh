#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/gtn}"
DB_PATH="${DB_PATH:-/var/lib/gtn/gtn.sqlite3}"
KEEP_COUNT="${KEEP_COUNT:-1}"
MIN_FREE_EXTRA_BYTES="${MIN_FREE_EXTRA_BYTES:-536870912}"
LOCK_PATH="${LOCK_PATH:-/run/lock/gtn-db-backup.lock}"

log() {
    printf '[gtn-db-backup] %s %s\n' "$(date '+%F %T')" "$*"
}

if ! [[ "$KEEP_COUNT" =~ ^[1-9][0-9]*$ ]]; then
    log "invalid KEEP_COUNT=$KEEP_COUNT"
    exit 2
fi

mkdir -p -- "$BACKUP_DIR"
umask 077

exec 9>"$LOCK_PATH"
if ! flock -n 9; then
    log "another backup is already running; skipped"
    exit 0
fi

if [[ ! -f "$DB_PATH" ]]; then
    log "database not found: $DB_PATH"
    exit 1
fi

# A killed backup may leave a large temporary file. It is never a valid restore
# point, so remove stale temporary files before checking available space.
find "$BACKUP_DIR" -maxdepth 1 -type f -name '.gtn-*.sqlite3.tmp.*' -mmin +360 \
    -delete

db_size="$(stat -c '%s' "$DB_PATH")"
available_bytes="$(df --output=avail -B1 "$BACKUP_DIR" | tail -n 1 | tr -d ' ')"
required_bytes=$((db_size + MIN_FREE_EXTRA_BYTES))
if (( available_bytes < required_bytes )); then
    log "insufficient free space; required=$required_bytes available=$available_bytes"
    exit 1
fi

stamp="$(date +%F-%H%M%S)"
final_path="$BACKUP_DIR/gtn-$stamp.sqlite3"
temp_path="$BACKUP_DIR/.gtn-$stamp.sqlite3.tmp.$$"

cleanup_temp() {
    rm -f -- "$temp_path"
}
trap cleanup_temp EXIT INT TERM

runner=(nice -n 15)
if command -v ionice >/dev/null 2>&1; then
    runner=(ionice -c 2 -n 7 "${runner[@]}")
fi

log "creating $final_path"
"${runner[@]}" sqlite3 "$DB_PATH" \
    ".timeout 5000" \
    ".backup '$temp_path'"

# Full quick_check scans every page and can saturate a small production host.
# Validate the file structure and essential schema using bounded reads instead.
backup_size="$(stat -c '%s' "$temp_path")"
if (( backup_size < db_size / 2 )); then
    log "backup is unexpectedly small; live=$db_size backup=$backup_size"
    exit 1
fi

read -r page_count page_size table_count has_users < <(
    sqlite3 -readonly -separator ' ' "$temp_path" \
        "SELECT
            (SELECT page_count FROM pragma_page_count),
            (SELECT page_size FROM pragma_page_size),
            (SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'),
            (SELECT COUNT(*) FROM sqlite_master
              WHERE type = 'table' AND name = 'users');"
)

if (( page_count <= 0 || page_size <= 0 || table_count <= 0 || has_users != 1 )); then
    log "backup validation failed; pages=$page_count page_size=$page_size tables=$table_count users=$has_users"
    exit 1
fi

expected_size=$((page_count * page_size))
if (( expected_size != backup_size )); then
    log "backup size does not match SQLite page metadata; expected=$expected_size actual=$backup_size"
    exit 1
fi

chmod 600 "$temp_path"
mv -- "$temp_path" "$final_path"
trap - EXIT INT TERM

# Delete older complete backups only after the new backup has been validated and
# atomically published. Timestamped names sort in creation order.
shopt -s nullglob
backups=("$BACKUP_DIR"/gtn-*.sqlite3)
if (( ${#backups[@]} > KEEP_COUNT )); then
    mapfile -t backups < <(printf '%s\n' "${backups[@]}" | sort -r)
    for old_backup in "${backups[@]:KEEP_COUNT}"; do
        rm -f -- "$old_backup"
        log "removed old backup $old_backup"
    done
fi

log "completed; bytes=$backup_size retained=$KEEP_COUNT"
