#!/bin/sh
# Backup PostgreSQL (pg_dump custom format). Usado manualmente ou pelo serviço backup no compose prod.
set -eu

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
PGHOST="${PGHOST:-db}"
PGUSER="${POSTGRES_USER:-postgres}"
PGDATABASE="${POSTGRES_DB:-motopay}"

mkdir -p "$BACKUP_DIR"
outfile="${BACKUP_DIR}/motopay_$(date +%Y%m%d_%H%M%S).dump"

if [ -n "${DATABASE_URL:-}" ]; then
  pg_dump "$DATABASE_URL" -Fc -f "$outfile"
else
  export PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}"
  pg_dump -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -Fc -f "$outfile"
fi

echo "Backup written to $outfile"
find "$BACKUP_DIR" -name 'motopay_*.dump' -type f -mtime +"$RETENTION_DAYS" -delete 2>/dev/null || true
