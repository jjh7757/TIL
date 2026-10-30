# FastAPI 컨테이너 실행하기

[Compose로 PostgreSQL 실행하기](Docker_Compose_PostgreSQL.md)에서 호스트로 실행하던 FastAPI를 이미지로 만들어 컨테이너로 실행하고 PostgreSQL과 연결합니다.

## Dockerfile에서 컨테이너까지

```
Dockerfile ──빌드──▶ 이미지 ──컨테이너 생성·시작──▶ 컨테이너
(만드는 방법)     (Python·라이브러리·앱 코드)    (FastAPI 실행)
```

Dockerfile을 저장하는 것만으로 이미지가 만들어지거나 서버가 실행되지는 않습니다. 이 실습은 `docker compose up -d --build`로 빌드와 실행을 진행합니다.

| 파일 | 설명하는 내용 |
|------|---------------|
| `Dockerfile` | FastAPI 이미지를 만드는 방법 |
| `compose.yaml` | 이미지로 컨테이너를 실행하고 연결하는 방법 |
| `.dockerignore` | 빌드에 보내지 않을 파일 |

PostgreSQL은 만들어진 이미지를 쓰고(`image`), FastAPI는 내 코드를 담아야 하므로 직접 빌드합니다(`build`).

## FastAPI Dockerfile

```dockerfile
FROM python:3.13-slim

WORKDIR /app
RUN pip install --no-cache-dir uv==0.13.6
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .

CMD ["uv", "run", "--no-sync", "fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
```

| 명령 | 역할 |
|------|------|
| `FROM` | 출발점 이미지(**베이스 이미지**) 선택 |
| `WORKDIR` | 이후 명령의 작업 폴더를 **이미지 안의** `/app`으로 지정. 없으면 생성. 컨테이너의 기본 작업 폴더로도 쓰임 |
| 첫 `RUN` | 이미지 안에 uv 설치 |
| 첫 `COPY` | 의존성 설정과 잠금 파일을 빌드 컨텍스트에서 `/app`으로 복사 |
| 둘째 `RUN` | 잠금 파일대로 라이브러리 설치 |
| 둘째 `COPY` | `.dockerignore`에 지정된 파일을 빼고 소스 복사 |
| `CMD` | 컨테이너 시작 시 실행할 기본 명령 |

- **`RUN`은 빌드 중**에 실행되어 결과가 이미지에 담기고, **`CMD`는 컨테이너 시작 시** 실행된다. 빌드 중에는 서버를 띄우지 않고 명령만 저장한다
- `--no-sync`: 빌드 때 설치한 환경을 그대로 사용
- `fastapi run`: 자동 재시작 없이 실행 (`fastapi[standard]`의 CLI)
- **의존성 파일과 코드를 나눠 복사**하는 이유: 코드만 바뀌면 라이브러리 설치 단계를 캐시에서 재사용

### `0.0.0.0`의 의미

해당 실행 환경의 **모든 네트워크 인터페이스**에서 요청을 받겠다는 뜻입니다. 컨테이너 안에서 `127.0.0.1`에만 바인딩하면 컨테이너 밖의 요청을 받을 수 없습니다. 브라우저에 입력하는 주소는 `0.0.0.0`이 아니라 호스트에 공개한 `http://localhost:8000`입니다.

### `.dockerignore`

```
.venv
.env
.env.*
__pycache__
*.pyc
.git
compose*.yaml
compose-examples/
```

- `.venv`: 라이브러리는 Dockerfile의 `RUN`으로 설치
- `.env`: API 키를 **이미지에 넣지 않고** 실행할 때 전달
- Compose 설정·예제 파일: 컨테이너 안에서 실행할 코드가 아님

## Compose에 backend 추가

기존 FastAPI 서버가 켜져 있으면 종료합니다.

```yaml
name: docker-practice

services:
  db:
    image: pgvector/pgvector:pg17-trixie
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: "1234"
      POSTGRES_DB: docker_prac
    ports:
      - "127.0.0.1:5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d docker_prac"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s

  backend:
    build: .
    env_file:
      - ./.env
    environment:
      DATABASE_URL: postgresql://postgres:1234@db:5432/docker_prac
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

### `build`

`build: .`는 `compose.yaml`이 있는 폴더로 이미지를 만들라는 뜻입니다. 이 폴더가 **빌드 컨텍스트**이며, Docker는 여기서 `Dockerfile`을 읽고 `COPY`할 파일을 찾습니다.

### `healthcheck` — DB 준비 상태 확인

PostgreSQL은 컨테이너가 시작된 뒤에도 초기화 시간이 필요합니다. 컨테이너 안에서 검사 명령을 반복 실행해 실제로 접속을 받을 준비가 됐는지 확인합니다.

| 옵션 | 의미 |
|------|------|
| `test` | 검사 명령. `CMD-SHELL`은 컨테이너 내부 셸에서 실행, `pg_isready`는 접속 준비 확인 프로그램 |
| `interval: 5s` | 검사 간격 |
| `timeout: 3s` | 한 번의 검사가 3초 안에 안 끝나면 실패 |
| `retries: 10` | 연속 10번 실패하면 `unhealthy` 표시 (**컨테이너 재시작 횟수가 아님**) |
| `start_period: 10s` | 시작 직후 최대 10초 동안 실패를 횟수에 넣지 않음 |

`start_period` 동안에도 검사는 실행됩니다. 그 사이 성공하면 바로 `healthy`가 되고 그때부터 실패를 셉니다.

### `depends_on` — DB가 준비된 뒤 시작

`condition: service_healthy`는 `db`의 healthcheck가 성공할 때까지 기다립니다.

```
DB 시작 → DB 준비 상태 검사 통과 → FastAPI 시작
```

FastAPI가 시작할 때 DB에 연결해 테이블을 만들기 때문에 필요합니다. 시작 후에도 검사는 계속되지만, 실행 중 DB 오류를 복구하거나 FastAPI를 재시작해 주지는 않습니다.

### `env_file`과 `environment`

- `env_file`: 파일의 값을 컨테이너 환경변수로 설정 (API 키 등)
- `environment`: Compose 파일에 직접 지정. **둘 다 있으면 `environment`가 우선**

| FastAPI 실행 방식 | `DATABASE_URL`의 호스트·포트 |
|-------------------|------------------------------|
| 로컬 FastAPI | `.env`의 `localhost:5433` |
| 컨테이너 FastAPI | Compose `environment`의 `db:5432` |

덕분에 로컬용 `.env`를 고치지 않아도 됩니다. Compose가 설정의 `${변수}`를 채우려고 읽는 `.env`와, `env_file`로 컨테이너에 전달하는 값은 역할이 다릅니다.

### 컨테이너 사이의 연결

Compose는 프로젝트의 기본 네트워크를 만들고 서비스를 연결하므로, 같은 네트워크에서는 **서비스 이름**으로 접속합니다.

```
내 컴퓨터의 브라우저 ─ localhost:8000 → 8000 ─▶ backend (FastAPI :8000)
                                                   │ db:5432
                                                   ▼
                                                 db (PostgreSQL :5432) ── postgres_data
```

- 백엔드 컨테이너에서 `localhost`는 **백엔드 컨테이너 자신**이다
- 컨테이너끼리는 실제 포트 **5432**, 호스트에 공개한 **5433**은 내 컴퓨터에서 접속할 때 쓴다
- `ports`의 `127.0.0.1`은 내 컴퓨터에서만 공개 포트에 접속하도록 제한한다

## 빌드와 실행

```bash
docker compose config -q
docker compose up -d --build
docker compose ps
docker compose logs backend
```

- `config -q`: 설정 유효성 검사. 아무것도 출력되지 않으면 정상
- `--build`: 이미지 빌드. 처음엔 Python 이미지 다운로드와 라이브러리 설치가 진행됨

`http://localhost:8000/docs`에서 `/health`, `/notes`를 호출합니다. 이제 호스트에서 `uv run`을 실행하지 않아도 되고, 같은 볼륨을 연결했으므로 저장한 메모도 조회됩니다. `POST /search`는 다음으로 확인합니다.

```json
{"query": "여러 컨테이너의 실행 설정을 한 파일로 관리하려면?"}
```

코드를 수정하면 이미지 안의 코드는 그대로이므로 다시 빌드합니다.

```bash
docker compose up -d --build backend
```

## Bind mount로 개발하기

`COPY`는 **빌드할 때** 코드를 복사하므로, 수정할 때마다 재빌드가 필요합니다. **Bind mount**는 내 컴퓨터의 파일·폴더를 컨테이너 경로에 연결해 이를 해결합니다.

| 방식 | 연결 대상 | 실습에서의 용도 |
|------|-----------|-----------------|
| 이름 있는 볼륨 | Docker가 관리하는 저장 공간 | PostgreSQL 데이터 유지 |
| Bind mount | 내 컴퓨터에서 지정한 파일·폴더 | 수정한 소스를 컨테이너에서 사용 |

### 개발용 설정 분리 — `compose.dev.yaml`

```yaml
services:
  backend:
    command: ["uv", "run", "--no-sync", "fastapi", "dev", "main.py", "--host", "0.0.0.0", "--port", "8000"]
    environment:
      WATCHFILES_FORCE_POLLING: "true"
    volumes:
      - ./main.py:/app/main.py
```

| 설정 | 의미 |
|------|------|
| `command` | Dockerfile의 `CMD` 대신 실행. `fastapi dev`는 코드 변경 시 자동 재시작 |
| `WATCHFILES_FORCE_POLLING` | 파일을 주기적으로 확인. Docker에서 변경 알림이 전달되지 않아도 감지 |
| `./main.py:/app/main.py` | `내 컴퓨터 경로:컨테이너 경로`. 이미지 안의 파일은 마운트 동안 **가려질 뿐** 이미지가 수정되지는 않음 |

Bind mount는 수정한 파일을 **보이게** 하고, `fastapi dev`는 변경을 **감지해 재시작**합니다. 둘 다 있어야 합니다.

### 실행

```bash
# 기본 설정: compose.yaml만 읽음 (compose.dev.yaml은 자동으로 읽지 않음)
docker compose up -d

# 개발용 설정: 두 파일을 합침
docker compose -f compose.yaml -f compose.dev.yaml config -q
docker compose -f compose.yaml -f compose.dev.yaml up -d
```

`main.py`의 제목을 고치고 저장한 뒤 `/docs`를 새로고침하면 재빌드 없이 반영됩니다. (서버 재시작과 브라우저 새로고침은 별개)

```python
app = FastAPI(title="Bind mount 개발 실습", lifespan=lifespan)
```

| 수정한 파일 | 반영 방법 |
|-------------|-----------|
| 마운트한 `main.py` | 자동 |
| Dockerfile, 의존성 파일, 마운트하지 않은 소스 | `docker compose -f compose.yaml -f compose.dev.yaml up -d --build` |

기본 설정으로 돌아가려면 `docker compose up -d`입니다. 이미지에 담긴 코드를 쓰므로, 수정한 코드까지 반영하려면 `docker compose up -d --build`를 실행합니다.
