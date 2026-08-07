#!/usr/bin/env bash
# Nightly PostgreSQL backup for Infrastructure Learning Lab.
#
# Dumps the learner-state database from the running postgres container into
# backups/learninglab-YYYYMMDD-HHMMSS.sql.gz and prunes dumps older than
# RETAIN_DAYS. Run from the repository root (cron example in
# docs/DEPLOYMENT.md §10). Restore with scripts/restore_db.sh.
set -euo pipefail

cd "$(dirname "$0")/.."
[ -f .env ] || { echo "ERROR: .env not found (run from a configured deployment)"; exit 1; }

# shellcheck disable=SC1091
set -a; source .env; set +a

BACKUP_DIR="backups"
RETAIN_DAYS="${BACKUP_RETAIN_DAYS:-14}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
OUT="${BACKUP_DIR}/learninglab-${STAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "Backing up ${POSTGRES_DB} -> ${OUT}"
docker compose exec -T postgres pg_dump \
    -U "${POSTGRES_USER}" \
    --clean --if-exists \
    "${POSTGRES_DB}" | gzip > "${OUT}"

# A zero-byte or tiny dump means something went wrong — fail loudly rather
# than silently rotating good backups away.
BYTES=$(stat -c%s "${OUT}")
if [ "${BYTES}" -lt 512 ]; then
    echo "ERROR: dump suspiciously small (${BYTES} bytes) — keeping it for inspection, exiting nonzero"
    exit 1
fi

echo "OK: ${BYTES} bytes"

find "${BACKUP_DIR}" -name 'learninglab-*.sql.gz' -mtime "+${RETAIN_DAYS}" -print -delete
