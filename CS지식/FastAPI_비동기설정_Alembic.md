# FastAPI 비동기 앱 초기 설정과 Alembic

`fastapi_agent` 프로젝트에 **환경 설정**(Pydantic Settings)과 **비동기 DB 연결**을 구성하고, **Alembic**으로 최초 테이블을 만든 뒤 `Post`에 `created_at`을 추가해 DB 구조를 변경합니다.

## 프로젝트 구조

```
src/
├── fastapi_agent/       # HTTP 요청·응답, 인증, 업무 규칙, 서비스 데이터 관리
│   ├── main.py          # 앱 생성과 라우터 등록
│   ├── core/            # 환경 설정, DB 연결, 보안 등 공통 기능
│   └── domains/         # 기능별 도메인
│       ├── users/
│       ├── posts/
│       ├── comments/
│       └── chat/
├── agents/              # 챗봇과 RAG Agent의 구성·실행
│   ├── chatbot/
│   └── rag/
└── rag/                 # 문서 로딩·분할, 임베딩, 벡터 저장소와 검색
```

- `domains/`는 회원·게시글·댓글·채팅처럼 **기능 영역(도메인) 기준**으로 나눈다 → 한 기능을 고칠 때 필요한 코드가 한 디렉터리에 모인다
- 각 도메인 안의 파일 역할

| 파일 | 담당 |
|------|------|
| `router.py` | 요청·응답 |
| `service.py` | 업무 규칙 |
| `repository.py` | DB 접근 |
| `models.py` | SQLAlchemy 모델 |
| `schemas.py` | Pydantic 요청·응답 모델 |

- AI가 필요한 도메인의 Service → `agents` 호출 → Agent가 필요하면 `rag`의 검색 사용
- `agents/rag`는 검색과 답변 생성을 잇는 **실행 흐름**, `src/rag`는 **문서 처리와 검색 기능** 자체

이전 실습(mysite4·mysite_db)이 `routers/`, `services/`처럼 **계층별 폴더**였다면, 여기서는 **도메인별 폴더 안에 계층 파일**을 둡니다.

## FastAPI에서 비동기를 쓰는 이유

게시글 API는 DB 결과를, AI 채팅 API는 외부 LLM 답변을 **기다립니다**. `async def` 경로 함수에서 비동기 DB·HTTP 호출을 `await`하면, 기다리는 동안 **이벤트 루프가 다른 요청을 처리**합니다.

```
요청 A: LLM API 호출 → 답변 대기 ─────────→ 답변 반환
요청 B:                     게시글 조회 → 응답
```

- 비동기 전환만으로 개별 쿼리나 LLM 답변 생성 **시간이 줄지는 않는다**. 대기 시간을 다른 요청에 활용할 뿐
- 일반 `def` 경로 함수도 FastAPI가 **스레드 풀**에서 실행하므로 동시 처리는 된다. 다만 동기 I/O를 기다리는 동안 **스레드를 점유**한다
- 비동기를 쓰려면 Router의 `async def` + DB 엔진·세션·외부 API 클라이언트도 비동기 API + Service·Repository를 `await`로 연결해야 한다

> **주의**: `async def` 안에서 **동기** DB·HTTP 호출을 직접 실행하면 그동안 이벤트 루프 전체가 막힌다. FastAPI는 Service·Repository의 일반 함수를 자동으로 스레드 풀에 보내주지 않는다.

## 작업 파일

| 파일 (`fastapi_agent/` 기준) | 작업 |
|------------------------------|------|
| `pyproject.toml` | 의존성, FastAPI 실행 진입점 |
| `.env` | DB 접속 정보, JWT 설정값 |
| `src/fastapi_agent/core/config.py` | 환경변수를 읽고 검증하는 설정 클래스 |
| `src/fastapi_agent/core/database.py` | 비동기 엔진·세션 |
| `src/fastapi_agent/domains/posts/models.py` | `Post`에 `created_at` 추가 |
| `alembic.ini`, `alembic/` | Alembic 설정, 테이블 생성·변경 마이그레이션 |
| `src/fastapi_agent/main.py` | lifespan에서 비동기 엔진 종료 |

## 실행 환경 준비

```bash
cd fastapi_agent
uv sync
```

| 패키지 | 용도 |
|--------|------|
| `fastapi[standard]` | API와 개발 서버 |
| `pydantic-settings` | 환경변수 읽기와 설정 검증 |
| `python-dotenv` | RAG 모듈에서 `.env` 로딩 |
| `sqlalchemy[asyncio]` | 비동기 ORM과 세션 |
| `psycopg[binary]` | PostgreSQL 드라이버 (동기·비동기 모두 지원) |
| `alembic` | 테이블 생성·변경과 이력 관리 |
| `pwdlib[argon2]` | Argon2 비밀번호 해싱·검증 |
| `pyjwt` | JWT 생성·검증 |
| `langchain`, `langchain-core` | 에이전트 구성, 메시지·문서·도구·Runnable 공통 요소 |
| `langchain-google-genai` | Gemini 채팅 모델, Google 임베딩 |
| `langgraph` | 상태·노드·분기로 RAG 실행 흐름 구성 |
| `langgraph-checkpoint-postgres` | 에이전트 상태를 PostgreSQL에 체크포인트로 저장·복원 |
| `langchain-community`, `pypdf` | `PyPDFLoader` 등 외부 연동, PDF 텍스트 추출 |
| `langchain-text-splitters` | 문서를 검색용 조각으로 분할 |
| `chromadb`, `langchain-chroma` | 벡터 저장·유사도 검색, LangChain 연동 |

```sql
CREATE DATABASE fastapi_agent;
```

## Pydantic Settings

### `.env`

```
DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/fastapi_agent
JWT_SECRET_KEY=생성한_64자리_비밀_키
JWT_EXPIRE_MINUTES=3000
DB_ECHO=false
```

`JWT_SECRET_KEY`는 `openssl rand -hex 32`로 생성합니다 (32바이트 = 16진수 64자).

### 설정 클래스

`os.getenv()`만 쓰면 `.env` 로딩, **타입 변환**, **필수 값 검사**를 직접 처리해야 합니다. Pydantic Settings는 클래스에 선언한 타입·조건대로 이를 처리합니다.

```python
# src/fastapi_agent/core/config.py
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(min_length=1)
    jwt_secret_key: SecretStr = Field(min_length=32)
    jwt_expire_minutes: int = Field(default=30, gt=0)
    db_echo: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

| 요소 | 의미 |
|------|------|
| 필드 이름 | 환경변수 이름과 대소문자 무관하게 매칭 (`database_url` ↔ `DATABASE_URL`) |
| `SecretStr` | 출력·로그에 `**********`로 표시. 실제 값은 `.get_secret_value()` |
| `"false"` → `bool` | 문자열 환경변수를 선언한 타입으로 변환 |
| `extra="ignore"` | `.env`에 클래스에 없는 변수(RAG용 API 키 등)가 있어도 오류 없음 |
| `@lru_cache` | 설정 객체를 캐시해 `get_settings()`를 다시 불러도 **같은 객체** 재사용 |

설정이 많아지면 DB·인증·AI 모델처럼 **역할별 설정 클래스**로 나눌 수도 있습니다.

## 비동기 DB 연결

`DATABASE_URL`은 동기 때와 같은 `postgresql+psycopg://...`입니다. 이 주소를 `create_async_engine()`에 넘기면 psycopg의 **비동기 연결**을 사용합니다.

| 동기 | 비동기 |
|------|--------|
| `create_engine()` | `create_async_engine()` |
| `sessionmaker()` | `async_sessionmaker()` |
| `Session` | `AsyncSession` |
| `def get_db()` | `async def get_db()` |
| `with SessionLocal()` | `async with SessionLocal()` |

```python
# src/fastapi_agent/core/database.py
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from fastapi_agent.core.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=settings.db_echo)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as db:   # 블록이 끝나면 세션이 닫힘 (try/finally 대신)
        yield db
```

### 왜 `expire_on_commit=False`인가

기본값 `True`는 commit 후 객체 속성을 **만료**시켜, 다음 접근 때 DB에서 다시 읽습니다. 그런데 Pydantic 응답 모델이 속성을 읽는 과정은 **동기**라서 이 재조회를 `await`할 수 없습니다. `False`로 두어 **이미 읽은 값을 유지**하고 응답에 사용합니다. ([세션과 객체 상태](SQLAlchemy_세션과객체상태.md) 참고)

## Alembic

**Alembic**은 SQLAlchemy와 함께 쓰는 **DB 마이그레이션 도구**입니다. 마이그레이션은 테이블 생성·컬럼 추가처럼 **DB 구조를 바꾸는 작업**입니다.

- 변경 내용을 **파일로 기록**하고 **순서대로** DB에 적용하며, 어디까지 적용했는지 관리한다
- 같은 파일로 개발·배포 환경 DB에 **동일한 변경**을 적용할 수 있다
- 앞선 `Base.metadata.create_all()`은 **없는 테이블만 생성**하고 기존 구조는 바꾸지 못했다 → 이 한계를 해결

### 마이그레이션 대상

Alembic은 `Base.metadata`와 **실제 DB 구조를 비교**해 변경 파일을 만듭니다.

| 모델 파일 | 클래스 | 테이블 |
|-----------|--------|--------|
| `domains/users/models.py` | `User` | `users` |
| `domains/posts/models.py` | `Post` | `posts` |
| `domains/comments/models.py` | `Comment` | `comments` |
| `domains/chat/models.py` | `ChatRoom`, `ChatMessage` | `chat_rooms`, `chat_messages` |

### 초기화

```bash
uv run alembic init -t async alembic     # 비동기 템플릿으로 alembic/ 생성
```

### `alembic/env.py` — DB와 모델 메타데이터 연결

```python
from fastapi_agent.core.config import get_settings
from fastapi_agent.core.database import Base
from fastapi_agent.domains.chat.models import ChatMessage, ChatRoom
from fastapi_agent.domains.comments.models import Comment
from fastapi_agent.domains.posts.models import Post
from fastapi_agent.domains.users.models import User

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
target_metadata = Base.metadata


def include_name(name, type_, parent_names):
    # 체크포인트 테이블은 AsyncPostgresSaver가 관리한다.
    checkpoint_tables = {"checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations"}
    return type_ != "table" or name not in checkpoint_tables


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata, include_name=include_name)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    engine = async_engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    if sys.platform == "win32":
        asyncio.run(
            run_async_migrations(),
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        )
    else:
        asyncio.run(run_async_migrations())
```

| 부분 | 이유 |
|------|------|
| 모델 모듈 import | import해야 테이블 정보가 `Base.metadata`에 등록된다. `Base`만 import하면 비교 대상이 누락됨 |
| `get_settings().database_url` | 접속 정보를 `alembic.ini`에 하드코딩하지 않고 `.env`에서 읽음 |
| `.replace("%", "%%")` | ini 설정 값에서 `%`는 보간 문자 → 비밀번호의 URL 인코딩(`%40` 등)이 깨지지 않게 이스케이프 |
| `include_name()` | LangGraph 체크포인터(`AsyncPostgresSaver`)가 따로 관리하는 테이블을 자동 감지에서 **제외** → autogenerate가 "모델에 없으니 삭제"하는 코드를 만들지 않음 |
| `connection.run_sync()` | Alembic 마이그레이션 자체는 동기 코드 → 비동기 연결 위에서 동기 함수로 실행 |
| `NullPool` | 마이그레이션은 한 번 실행하고 끝나므로 연결 풀 불필요 |
| Windows `SelectorEventLoop` | psycopg 비동기는 Windows 기본 `ProactorEventLoop`에서 동작하지 않음 |

### 최초 테이블 생성

```bash
uv run alembic revision --autogenerate -m "create initial tables"
```

`alembic/versions/<revision_id>_create_initial_tables.py`가 생성됩니다. revision ID는 실행마다 다릅니다. 이 명령은 **파일만 생성**하고 테이블을 만드는 SQL은 실행하지 않습니다. (프로젝트에 초기 파일이 이미 있으면 내용을 확인하고 바로 적용)

```bash
uv run alembic upgrade head
```

`head`는 마이그레이션 파일들의 **최신 버전**. `upgrade head`는 DB에 아직 적용하지 않은 파일의 `upgrade()`를 순서대로 실행합니다.

### 모델 변경: `Post`에 `created_at` 추가

```python
# src/fastapi_agent/domains/posts/models.py (추가할 부분)
from datetime import datetime

from sqlalchemy import DateTime, func


class Post(Base):
    # 기존 컬럼과 관계 정의는 유지
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
```

- `DateTime(timezone=True)`: PostgreSQL `timestamptz` (시간대 포함)
- `server_default=func.now()`: 값을 생략한 INSERT에서 **DB가** 현재 **트랜잭션 시작 시각**을 채운다 (파이썬 `default`와 달리 DB 테이블 정의에 기본값이 들어감)

모델을 고쳐도 DB 구조는 **자동으로 바뀌지 않습니다**. 초기 파일은 그대로 두고 **새 마이그레이션**을 만듭니다.

```bash
uv run alembic revision --autogenerate -m "add post created_at"
```

```python
def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
```

- 새 파일의 `down_revision`이 초기 마이그레이션 ID를 가리키는지 확인 → 파일끼리 **연결 리스트**처럼 순서가 이어진다
- autogenerate 결과는 **반드시 직접 검토**: 의도한 변경만 있는지, 의도하지 않은 삭제는 없는지
- 기존 행이 있는 테이블에 `nullable=False` 컬럼을 추가해도 `server_default`가 있어 기존 행이 채워지므로 실패하지 않는다

```bash
uv run alembic upgrade head
```

DB 관리 도구에서 `posts`에 `created_at`이 생겼는지 확인합니다.

## 앱 실행

### lifespan

```python
# src/fastapi_agent/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from fastapi_agent.core.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(lifespan=lifespan)
```

| 시점 | 실행 |
|------|------|
| `yield` 전 | 공용 자원 준비 (이 예제는 추가 초기화 없음) |
| `yield` 동안 | FastAPI가 요청 처리 |
| 앱 종료 | `await engine.dispose()`로 연결 풀 정리 |

mysite_db와 달리 **`create_all()`을 lifespan에서 호출하지 않습니다**. 테이블 생성·변경은 Alembic 명령으로만 적용합니다.

### 실행 진입점

```toml
[tool.fastapi]
entrypoint = "fastapi_agent.main:app"
```

`fastapi_agent.main`은 `src/fastapi_agent/main.py`, `app`은 그 안의 FastAPI 객체입니다. `uv sync`로 패키지를 설치해 쓰므로 모듈 경로에 `src`를 넣지 않습니다.

```bash
uv run fastapi dev        # 진입점에서 앱을 불러와 http://127.0.0.1:8000 실행, 코드 변경 시 자동 재시작
```
