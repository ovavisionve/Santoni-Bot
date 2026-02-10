#!/usr/bin/env bash
# ============================================
# SantoniBot - Database Backup Script
# Run via cron: 0 2 * * * /opt/santonibot/scripts/backup.sh
# ============================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

echo "SantoniBot Backup - $DATE"

# ---- PostgreSQL backup ----
echo "Backing up PostgreSQL..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T db \
    pg_dump -U santonibot santonibot | gzip > "$BACKUP_DIR/santonibot_db_$DATE.sql.gz"

echo "Backup saved: santonibot_db_$DATE.sql.gz"

# ---- Clean old backups ----
echo "Cleaning backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

echo "Backup complete."
ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | tail -5
