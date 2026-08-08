#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/manar_qc}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PASSPHRASE="${BACKUP_PASSPHRASE:-ManarBackup2026!}"

mkdir -p "$BACKUP_DIR"

echo "=== Manar QC Backup Starting: $TIMESTAMP ==="

# 1. Postgres Database Dump
DB_CONTAINER=$(docker ps -q -f name=manar-qc-db-1 || docker ps -q -f name=manar_qc_db)
if [ -n "$DB_CONTAINER" ]; then
    echo "Dumping database..."
    docker exec "$DB_CONTAINER" pg_dump -U manar manar_qc | \
        gpg --symmetric --batch --passphrase "$PASSPHRASE" \
        -o "$BACKUP_DIR/db_$TIMESTAMP.sql.gpg"
    echo "Database dump saved to $BACKUP_DIR/db_$TIMESTAMP.sql.gpg"
else
    echo "WARNING: Database container not found!"
fi

# 2. Prune old backups (keep 30 days)
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "=== Backup Complete ==="
