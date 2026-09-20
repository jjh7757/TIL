# 공용 DB 서버 구성 — PostgreSQL + Redis

앱은 [README](README.md)·[새앱배포절차.md](새앱배포절차.md) 덕분에 `git push`만으로 즉시 배포되지만,
DB는 그 흐름에 없었다. 이 문서대로 서버에 공용 DB를 **한 번** 올려두면,
그 뒤로는 새 프로젝트마다 database 하나씩만 만들어서 붙이면 된다.

관련: [환경정보.md](환경정보.md), [rag앱배포기록.md](rag앱배포기록.md)

## 왜 이렇게 구성하는가

- **왜 앱마다 컨테이너를 새로 안 띄우는가** — RAM 2GB([새앱배포절차.md의 제약](새앱배포절차.md))에서
  Postgres 인스턴스를 프로젝트마다 띄우면 금방 바닥난다. 컨테이너 하나를 공유하고
  database/사용자만 나누면 고정 오버헤드가 한 번만 든다.
- **왜 PostgreSQL인가 (MySQL이 근소하게 더 많았는데도)** — 원티드 "서버 개발자" 공고
  628건(2026-09-20 기준)의 기술스택 태그를 조사한 결과 MySQL 38건 · PostgreSQL 35건 ·
  Redis 33건으로 상위 세 개가 사실상 동률이었다. 그중 PostgreSQL을 고른 이유는 채용 수요 차이가
  아니라 `pgvector` 확장으로 [rag 앱](rag앱배포기록.md)류의 벡터 검색까지 같은 DB로 흡수할 수
  있어서다 — MySQL엔 이 옵션이 없다. MySQL 스펙이 더 중요하면 이미지만 바꿔도 이 구조 그대로 쓴다.
- **왜 Redis도 기본에 넣는가** — 세션·캐시는 거의 모든 백엔드 프로젝트에 필요하고, 위 조사에서도
  단독 3위였다.
- **왜 외부에 노출하지 않는가** — "호스트 포트는 Caddy만 연다"는 기존 원칙을 그대로 따른다.
  DB는 `web` 네트워크 안에서 컨테이너 이름(`postgres`, `redis`)으로만 접근된다.

## 구조

```
EC2 t4g.small
   ├─ Caddy     :80 :443        서브도메인 라우팅 (기존)
   ├─ postgres  :5432 (내부만)   database별로 앱을 나눠 공유
   ├─ redis     :6379 (내부만)   DB 인덱스로 앱을 나눠 공유
   ├─ app-a  ──┐
   └─ app-b  ──┴─▶ web 네트워크 안에서 postgres:5432 / redis:6379 로 접근
```

## RAM 예산 재계산

DB를 올리고 나면 새앱배포절차.md의 "앱 2개는 편하고 3개는 빡빡하다"가
**"앱 1~2개 + DB"로 좁혀진다.**

| | 사용 |
|---|---|
| OS + Docker | 약 300MB |
| Caddy | 약 50MB |
| **postgres** | 상한 256MB |
| **redis** | 상한 128MB |
| 앱 (상한 768MB) | 앱마다 |
| **여유** | **약 1.3GB** |

부족하면 인스턴스 타입을 올린다(README의 "RAM 2GB가 실질 제약" 절과 동일한 트레이드오프 —
t4g.small을 벗어나면 2026-12-31까지의 무료 트라이얼 대상에서 빠진다).

## 결정 사항

| 항목 | 선택 | 이유 |
|---|---|---|
| 이미지 | `postgres:16-alpine`, `redis:7-alpine` | 가볍고 arm64 공식 지원 |
| 격리 방식 | 컨테이너 공유 + database/role(Postgres), DB 인덱스(Redis)로 논리 분리 | RAM 절약. [왜](#왜-이렇게-구성하는가) 참고 |
| 위치 | `/srv/db/docker-compose.yml` | 앱과 동일한 디렉토리 규칙 |
| 네트워크 | `web` (외부 미노출) | 기존 원칙과 동일 |
| 인증 | 앱마다 전용 Postgres role, Redis는 공용 비밀번호 + DB 인덱스 | Redis 커뮤니티 버전은 DB 단위 ACL이 약해 비밀번호까지는 못 나눈다 |
| 백업 | 매일 `pg_dumpall` → `/srv/db/backups`, 7일 보관 | 인스턴스 하나가 여러 앱의 데이터를 갖게 되므로 최소 안전망 필요 |

## 최초 1회 설정 — Session Manager

```bash
sudo mkdir -p /srv/db && sudo chown ubuntu:ubuntu /srv/db
```

```bash
sudo tee /srv/db/docker-compose.yml >/dev/null <<'EOF'
services:
  postgres:
    image: postgres:16-alpine
    container_name: postgres
    restart: unless-stopped
    env_file:
      - .env
    environment:
      POSTGRES_USER: postgres
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - web
    command: postgres -c shared_buffers=64MB -c max_connections=50
    deploy:
      resources:
        limits:
          memory: 256M
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s

  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - redisdata:/data
    networks:
      - web
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 96mb --maxmemory-policy allkeys-lru
    deploy:
      resources:
        limits:
          memory: 128M
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "--no-auth-warning", "ping"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

networks:
  web:
    external: true

volumes:
  pgdata:
  redisdata:
EOF
```

> 원본은 [templates/db/docker-compose.yml](templates/db/docker-compose.yml) — 수정하면 여기 사본도 같이 갱신할 것.

```bash
sudo tee /srv/db/.env >/dev/null <<'EOF'
POSTGRES_PASSWORD=<openssl rand -base64 24 로 생성>
REDIS_PASSWORD=<openssl rand -base64 24 로 생성>
EOF
sudo chmod 600 /srv/db/.env
```

```bash
cd /srv/db && docker compose up -d
docker compose ps        # 둘 다 healthy 될 때까지 대기
```

백업 스크립트도 같이 올린다.

```bash
sudo tee /srv/db/backup.sh >/dev/null <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR=/srv/db/backups
KEEP_DAYS=7
TS="$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
docker exec postgres pg_dumpall -U postgres | gzip > "$BACKUP_DIR/pgdumpall_$TS.sql.gz"
find "$BACKUP_DIR" -name 'pgdumpall_*.sql.gz' -mtime "+$KEEP_DAYS" -delete
EOF
sudo chmod +x /srv/db/backup.sh
( sudo crontab -l 2>/dev/null; echo "0 4 * * * /srv/db/backup.sh >> /var/log/db-backup.log 2>&1" ) | sudo crontab -
```

> 원본(로그 출력 포함)은 [templates/db/backup.sh](templates/db/backup.sh). 복구는
> `gunzip -c pgdumpall_20260920.sql.gz | docker exec -i postgres psql -U postgres`.

## 새 프로젝트에 DB 붙이기 — 매번 반복

앱 이름을 `rag`, 비밀번호를 `<pw>`로 가정한다. 실제로는 `openssl rand -base64 18` 정도로 생성해서 쓴다.

**1. Postgres에 database + role 생성**

```bash
docker exec -it postgres psql -U postgres
```

```sql
CREATE ROLE rag WITH LOGIN PASSWORD '<pw>';
CREATE DATABASE rag OWNER rag;
\q
```

**2. Redis는 DB 인덱스만 하나 배정** — 프로젝트마다 0~15 중 안 쓰는 번호를 고른다.
[환경정보.md](환경정보.md)에 앱별로 어떤 인덱스를 썼는지 적어두면 나중에 안 겹친다.

**3. 앱의 `.env`에 연결 정보 추가** (`/srv/<앱>/.env`, 서버에만 두고 커밋하지 않음)

```bash
DATABASE_URL=postgresql://rag:<pw>@postgres:5432/rag
REDIS_URL=redis://:<REDIS_PASSWORD>@redis:6379/1
```

**4. 연결 확인**

```bash
docker exec -it <앱 컨테이너> sh -c 'echo $DATABASE_URL'   # 값이 제대로 들어갔는지
docker compose -f /srv/<앱>/docker-compose.yml restart      # .env 반영은 재시작해야 적용됨
docker compose -f /srv/<앱>/docker-compose.yml logs -f      # 앱이 DB 연결에 성공하는지
```

앱의 `docker-compose.yml` 자체는 바꿀 게 없다 — 이미 `web` 네트워크에 붙어 있으므로
`postgres`/`redis` 호스트명이 그대로 resolve된다.

## 주의할 점

- **Redis는 캐시/세션 전용이다.** `allkeys-lru`라 메모리가 차면 오래된 키부터 지워진다.
  영속이 필요한 데이터를 Redis에만 두면 안 된다 — 그런 데이터는 Postgres로.
- **앱 커넥션 풀을 작게 유지한다.** `max_connections=50`을 여러 앱이 나눠 쓰므로 앱 하나가
  기본 풀 크기(예: 20~30)를 그대로 쓰면 다른 앱 배포 때 연결이 거부될 수 있다. 5~10개로 제한할 것.
- **role 권한은 자기 database로만 좁힌다.** `CREATE ROLE ... LOGIN` 정도만 주고, 다른 앱의
  database에는 애초에 권한이 없으므로 건드릴 수 없다.
- **비밀번호는 `.env`에만.** `환경정보.md`에는 어떤 앱이 어떤 database/Redis 인덱스를 쓰는지 같은
  식별자만 남기고 비밀번호는 적지 않는다(기존 원칙과 동일).

## 문제가 생기면

| 증상 | 확인할 것 |
|---|---|
| 앱에서 `connection refused` | `docker network inspect web`으로 앱·db 컨테이너가 같은 네트워크에 있는지 |
| `too many connections` | 각 앱의 커넥션 풀 상한을 낮춘다. 급하면 `max_connections` 조정 후 postgres 재기동 |
| `password authentication failed` | 앱 `.env`의 비밀번호와 `psql`로 만든 role의 비밀번호가 일치하는지 |
| Redis 키가 예상보다 빨리 사라짐 | `allkeys-lru` + `maxmemory 96mb` 한도 확인. 캐시가 아니라 영속 데이터면 설계를 바꿀 것 |
| 배포(재시작) 후에도 `.env` 값이 안 바뀜 | `docker compose restart`가 아니라 `docker compose up -d`가 필요한 경우가 있다 (env_file 변경은 재생성 필요) |

## 체크리스트

- [ ] `/srv/db/docker-compose.yml` + `.env` (POSTGRES_PASSWORD, REDIS_PASSWORD)
- [ ] `docker compose up -d` 후 둘 다 healthy
- [ ] `backup.sh` + cron 등록
- [ ] (새 프로젝트마다) role + database 생성
- [ ] (새 프로젝트마다) Redis DB 인덱스 배정, [환경정보.md](환경정보.md)에 기록
- [ ] 앱 `.env`에 `DATABASE_URL` / `REDIS_URL` 추가
- [ ] 앱 재기동 후 연결 로그 확인
