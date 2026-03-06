#!/bin/bash
# Moonjar PMS — Database Backup Script
# Usage: ./scripts/backup.sh [--upload]
# Cron: 0 2 * * * /path/to/scripts/backup.sh --upload

set -euo pipefail

# Load environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../.env" 2>/dev/null || true

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/tmp/moonjar-backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/moonjar_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting database backup..."

# Dump database
pg_dump "${DATABASE_URL}" | gzip > "${BACKUP_FILE}"

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[$(date)] Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Encrypt if GPG key available
if [ -n "${BACKUP_GPG_KEY:-}" ]; then
    gpg --encrypt --recipient "${BACKUP_GPG_KEY}" "${BACKUP_FILE}"
    rm "${BACKUP_FILE}"
    BACKUP_FILE="${BACKUP_FILE}.gpg"
    echo "[$(date)] Encrypted with GPG key: ${BACKUP_GPG_KEY}"
fi

# Upload to S3 if --upload flag
if [ "${1:-}" = "--upload" ] && [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    aws s3 cp "${BACKUP_FILE}" "s3://${BACKUP_S3_BUCKET}/backups/$(basename ${BACKUP_FILE})"
    echo "[$(date)] Uploaded to s3://${BACKUP_S3_BUCKET}/backups/"
fi

# Cleanup old backups
find "${BACKUP_DIR}" -name "moonjar_*.sql.gz*" -mtime "+${RETENTION_DAYS}" -delete
echo "[$(date)] Cleaned up backups older than ${RETENTION_DAYS} days"

echo "[$(date)] Backup complete!"
