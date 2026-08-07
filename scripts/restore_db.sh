#!/usr/bin/env bash
# Restore a PostgreSQL backup produced by scripts/backup_db.sh.
#
# Usage:
#   ./scripts/restore_db.sh backups/learninglab-YYYYMMDD-HHMMSS.sql.gz
#   ./scripts/restore_db.sh --target learninglab_restore_test backups/....sql.gz
#
# Without --target this restores into the REAL database (destructive: the
# dump carries --clean, so existing tables are dropped and recreated).
# With --target it restores into a scratch database instead — use that to
# VERIFY a backup before you ever need it in anger (docs/DEPLOYMENT.md §11).
set -euo pipefail

cd "$(dirname "$0")/.."
[ -f .env ] || { echo "ERROR: .env not found"; exit 1; }
# shellcheck disable=SC1091
set -a; source .env; set +a

TARGET_DB="${POSTGRES_DB}"
if [ "${1:-}" = "--target" ]; then
    TARGET_DB="$2"; shift 2
fi
DUMP="${1:?usage: restore_db.sh [--target dbname] <dump.sql.gz>}"
[ -f "${DUMP}" ] || { echo "ERROR: ${DUMP} not found"; exit 1; }

if [ "${TARGET_DB}" = "${POSTGRES_DB}" ]; then
    echo "About to OVERWRITE the live database '${TARGET_DB}' from ${DUMP}."
    read -r -p "Type the database name to confirm: " CONFIRM
    [ "${CONFIRM}" = "${TARGET_DB}" ] || { echo "Aborted."; exit 1; }
else
    # Scratch-database path: create it if missing so verification is one command.
    docker compose exec -T postgres psql -U "${POSTGRES_USER}" -d postgres \
        -tc "SELECT 1 FROM pg_database WHERE datname='${TARGET_DB}'" | grep -q 1 || \
    docker compose exec -T postgres createdb -U "${POSTGRES_USER}" "${TARGET_DB}"
fi

echo "Restoring ${DUMP} into ${TARGET_DB}..."
gunzip -c "${DUMP}" | docker compose exec -T postgres psql \
    -U "${POSTGRES_USER}" -d "${TARGET_DB}" --set ON_ERROR_STOP=on -q

echo "Row counts in ${TARGET_DB}:"
docker compose exec -T postgres psql -U "${POSTGRES_USER}" -d "${TARGET_DB}" -c \
    "SELECT relname AS table, n_live_tup AS approx_rows FROM pg_stat_user_tables ORDER BY relname;"

echo "Done. (If this was a --target verification, drop it with:"
echo "  docker compose exec postgres dropdb -U ${POSTGRES_USER} ${TARGET_DB})"
