# Docker Compose로 PostgreSQL 실행하기 — 볼륨과 pgvector

[Docker 기초](Docker기초.md)에 이어 PostgreSQL을 컨테이너로 실행하고, 호스트의 FastAPI를 연결하고, 볼륨으로 데이터를 유지하고, pgvector로 벡터 검색까지 해 봅니다.

## Compose 프로젝트와 서비스

`compose.yaml`은 YAML 설정 파일입니다. 들여쓰기로 구조를 구분하므로 탭 대신 2칸 공백을 씁니다.

```yaml
name: docker-practice

services:
  db:
    image: postgres:17
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: "1234"
      POSTGRES_DB: docker_prac
    ports:
      - "127.0.0.1:5433:5432"
```

| 항목 | 의미 |
|------|------|
| `name` | 프로젝트 이름. 관련 컨테이너·네트워크·볼륨을 구분 |
| `services` | 실행할 서비스들. 각 서비스는 **별도 컨테이너**로 실행 |
| `db` | 직접 정한 서비스 이름 |
| `image` | 사용할 이미지. `postgres`는 이름, `17`은 메이저 버전 태그 |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | 처음 만들 사용자, 비밀번호, 데이터베이스 |
| `ports` | 호스트 포트를 컨테이너 포트에 연결 |

`POSTGRES_*` 값은 이미지가 **빈 데이터 디렉터리를 처음 초기화할 때만** 쓰입니다. 이미 데이터가 있는 볼륨을 연결하면 값을 바꿔도 기존 사용자·비밀번호가 바뀌지 않습니다. 예제 비밀번호는 로컬 실습용입니다.

### 포트 읽기

```
127.0.0.1 : 5433 : 5432
호스트 주소  호스트 포트  컨테이너 포트
```

호스트 포트와 컨테이너 내부 포트는 **별개**입니다. 로컬 PostgreSQL이 호스트의 5432를 쓰고 있으므로 호스트 5433을 컨테이너 5432에 연결합니다.

| 접속 주소 | 연결 대상 |
|-----------|-----------|
| `localhost:5432` | 로컬에 설치한 PostgreSQL |
| `localhost:5433` | 컨테이너의 PostgreSQL |

### 실행과 중지

```bash
docker compose up -d
docker compose ps
docker compose logs db
```

- `up`: 설정대로 컨테이너를 만들고 실행. 이미지가 없으면 내려받음
- `-d`: 백그라운드 실행 후 터미널을 돌려줌
- `logs db`에서 `database system is ready to accept connections`를 확인 (Docker Desktop의 Containers → `docker-practice`에서도 확인 가능)

DB 접속은 VSCode의 Database Client 확장으로 합니다.

| 명령 | 동작 |
|------|------|
| `docker compose stop` | 컨테이너를 남겨 두고 중지 |
| `docker compose start` | 중지된 컨테이너를 다시 시작 |
| `docker compose restart db` | DB 컨테이너 재시작 |
| `docker compose down` | 프로젝트의 컨테이너와 기본 네트워크 **삭제** |
| `docker compose up -d` | 설정에 맞게 컨테이너를 생성하거나 실행 |

중지와 삭제는 다릅니다. 위 명령으로 이미지는 삭제되지 않습니다.

## 로컬 FastAPI와 DB 연결

호스트에서 FastAPI를 실행하고 PostgreSQL 컨테이너에 메모를 저장합니다.

```bash
docker compose ps -a db      # Up이면 실행 중
docker compose up -d db      # 없거나 실행 중이 아닐 때만
```

| 메서드 | 경로 | 기능 |
|--------|------|------|
| GET | `/health` | 앱과 DB 연결 확인 |
| POST | `/notes` | 메모 저장 |
| GET | `/notes` | 최근 메모 최대 20개 조회 |
| POST | `/search` | pgvector에 저장한 텍스트 검색 |

```
# .env (load_dotenv()가 읽음)
DATABASE_URL=postgresql://postgres:1234@localhost:5433/docker_prac
GEMINI_API_KEY=
```

```bash
uv sync
uv run fastapi dev main.py
```

```
브라우저 ─ localhost:8000 ─▶ 로컬 FastAPI ─ localhost:5433 ─▶ 호스트 포트 5433 ─▶ PostgreSQL 컨테이너 :5432
```

FastAPI가 **호스트에서** 실행되므로 `localhost`는 내 컴퓨터이고, DB에는 공개된 호스트 포트 5433으로 접속합니다.

`/docs`에서 `GET /health` → `{"status": "ok"}`, `POST /notes`에 `{"text": "Compose로 PostgreSQL 연결 성공"}`을 넣고 `GET /notes`로 확인합니다.

## 볼륨으로 데이터 유지

### 볼륨이 없으면

1. `POST /notes`로 메모 저장
2. `docker compose down`으로 컨테이너 삭제
3. `docker compose up -d`로 다시 만들고 FastAPI 재실행
4. `GET /notes` → **빈 목록**

컨테이너 자체에 저장한 데이터는 컨테이너와 함께 사라집니다.

### 이름 있는 볼륨

```yaml
name: docker-practice

services:
  db:
    image: postgres:17
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: "1234"
      POSTGRES_DB: docker_prac
    ports:
      - "127.0.0.1:5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

- 최상위 `volumes`: 사용할 볼륨 **정의**
- `db.volumes`: 그 볼륨을 컨테이너 경로에 **연결**
- `/var/lib/postgresql/data`: PostgreSQL 17 데이터 경로
- 새 이름의 볼륨을 연결하면 빈 DB로 시작

### 확인

1. 메모 저장: `{"text": "컨테이너를 다시 만들어도 남을 메모"}`
2. `docker compose down` → `docker compose up -d`
3. 준비 완료 로그 확인 후 FastAPI 재실행
4. `GET /notes` → 삭제 전 메모의 `id`, `text`가 그대로 남아 있음

새 컨테이너가 같은 볼륨을 연결하기 때문입니다. Docker Desktop의 Volumes에서 `docker-practice_postgres_data`(프로젝트 이름 + 볼륨 이름)도 확인할 수 있습니다.

> `docker compose down`은 이름 있는 볼륨을 지우지 않는다. `docker compose down -v`는 볼륨까지 삭제하므로 데이터가 사라진다.

## PostgreSQL을 벡터 DB로 — pgvector

**pgvector**는 PostgreSQL에 벡터 저장과 유사도 검색을 추가하는 확장 기능입니다. 메모 같은 일반 데이터와 임베딩을 **같은 PostgreSQL**에서 관리할 수 있어 별도 DB 서버가 필요 없습니다.

```yaml
services:
  db:
    image: pgvector/pgvector:pg17-trixie   # image만 변경, 나머지는 위와 동일
```

PostgreSQL 17에 pgvector가 설치된 이미지입니다. 서비스 이름, 접속 정보, 데이터 경로, 볼륨 이름을 유지하므로 **같은 PostgreSQL 17 데이터**를 그대로 씁니다.

```bash
docker compose up -d db
```

```
# .env — 임베딩에 Gemini API를 호출하므로 유효한 키 필요
DATABASE_URL=postgresql://postgres:1234@localhost:5433/docker_prac
GEMINI_API_KEY=발급받은_API_키
```

Python에서는 `langchain-postgres`의 `PGVectorStore`로 사용합니다.

### 등록과 검색

```bash
uv sync
uv run ingest.py      # 문자열 6개(이미지·Compose·볼륨·FastAPI·LangGraph·React)를 임베딩해 저장
uv run retriever.py   # 검색 예제 실행
```

`ingest.py`는 같은 ID로 저장하므로 **다시 실행해도 문서가 늘어나지 않습니다**.

```python
# retriever.py
if __name__ == "__main__":
    query = "컨테이너를 삭제해도 데이터를 유지하려면 어떻게 해야 하나요?"
    for document in search(query):
        print(document.page_content)
```

직접 실행할 때만 `if __name__ == "__main__":` 아래가 동작하고, 관련 텍스트 두 개가 출력됩니다. FastAPI도 같은 `search()`를 호출합니다.

```bash
uv run fastapi dev main.py
```

`/docs`의 `POST /search`에 입력:

```json
{"query": "컨테이너를 삭제해도 데이터를 유지하려면 어떻게 해야 하나요?"}
```
