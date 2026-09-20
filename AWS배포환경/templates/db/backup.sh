#!/usr/bin/env bash
# /srv/db/backup.sh — cron으로 매일 실행
# 사용법: crontab -e (root) 에 한 줄 추가
#   0 4 * * * /srv/db/backup.sh >> /var/log/db-backup.log 2>&1
set -euo pipefail

BACKUP_DIR=/srv/db/backups
KEEP_DAYS=7
TS="$(date +%Y%m%d)"

mkdir -p "$BACKUP_DIR"

echo "==> pg_dumpall ($TS)"
docker exec postgres pg_dumpall -U postgres | gzip > "$BACKUP_DIR/pgdumpall_$TS.sql.gz"

echo "==> ${KEEP_DAYS}일 지난 백업 정리"
find "$BACKUP_DIR" -name 'pgdumpall_*.sql.gz' -mtime "+$KEEP_DAYS" -delete

echo "==> 완료: $BACKUP_DIR/pgdumpall_$TS.sql.gz"

# 복구:
#   gunzip -c pgdumpall_20260920.sql.gz | docker exec -i postgres psql -U postgres
