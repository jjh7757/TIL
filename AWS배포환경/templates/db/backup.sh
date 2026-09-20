#!/usr/bin/env bash
# /srv/db/backup.sh — cron으로 매일 실행
# 사용법: crontab -e (root) 에 한 줄 추가
#   0 4 * * * /srv/db/backup.sh >> /var/log/db-backup.log 2>&1
set -euo pipefail

BACKUP_DIR=/srv/db/backups
KEEP_DAYS=7
S3_BUCKET=ai-agent-develop-db-backup-403187831140
TS="$(date +%Y%m%d)"
FILE="pgdumpall_$TS.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "==> pg_dumpall ($TS)"
docker exec postgres pg_dumpall -U postgres | gzip > "$BACKUP_DIR/$FILE"

echo "==> S3 업로드 (오프사이트 — 이 EC2·EBS 볼륨이 통째로 사라져도 살아남는다)"
aws s3 cp "$BACKUP_DIR/$FILE" "s3://$S3_BUCKET/$FILE" --region ap-northeast-2

echo "==> 로컬 ${KEEP_DAYS}일 지난 백업 정리 (S3는 버킷 수명주기 규칙이 30일 뒤 자동 정리)"
find "$BACKUP_DIR" -name 'pgdumpall_*.sql.gz' -mtime "+$KEEP_DAYS" -delete

echo "==> 완료: $BACKUP_DIR/$FILE (+ s3://$S3_BUCKET/$FILE)"

# 복구 (로컬 백업이 있을 때):
#   gunzip -c pgdumpall_20260920.sql.gz | docker exec -i postgres psql -U postgres
# 복구 (S3에서 받아와야 할 때 -- 서버 역할엔 GetObject가 없으므로 로컬 admin으로 presigned URL 발급):
#   로컬:  URL=$(aws s3 presign s3://ai-agent-develop-db-backup-403187831140/pgdumpall_20260920.sql.gz --expires-in 300)
#   서버:  curl -sS "$URL" | gunzip | docker exec -i postgres psql -U postgres
# 상세·실제 검증 기록: ../../DB환경구성.md
