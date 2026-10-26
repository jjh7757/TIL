# FastAPI DB 연동 — PostgreSQL + SQLAlchemy 게시판

앞선 [FastAPI 레이어드 아키텍처](FastAPI_레이어드아키텍처.md)의 mysite4는 게시글을 **메모리 리스트**에 저장해서 서버를 재시작하면 데이터가 사라졌습니다. mysite_db는 같은 Router·Service·Repository 구조를 유지한 채 **Repository의 저장소만 PostgreSQL로** 바꿔, 재시작해도 데이터가 유지되게 합니다.

ORM 문법 자체는 [SQLAlchemy ORM 기초](SQLAlchemy_ORM.md)에 따로 정리했습니다.

## API 목록

| 메서드 | URL | 설명 | 성공 상태 코드 |
|--------|-----|------|----------------|
| POST | `/posts-db` | 게시글 등록 | 201 |
| GET | `/posts-db` | 게시글 목록 조회 | 200 |
| GET | `/posts-db/{id}` | 게시글 상세 조회 | 200 |
| PUT | `/posts-db/{id}` | 게시글 제목과 내용 수정 | 200 |
| DELETE | `/posts-db/{id}` | 게시글 삭제 | 204 |

## 프로젝트 구조

```
fastapi_basic/
├── .env
├── database.py              # Engine, SessionLocal, Base, get_db
├── main.py                  # lifespan(테이블 생성), Router 등록
└── mysite_db/
    ├── models/
    │   ├── __init__.py      # 모델 등록
    │   └── post.py          # SQLAlchemy 모델 (테이블)
    ├── schemas/post.py      # Pydantic 스키마 (요청·응답)
    ├── repositories/post_repository.py
    ├── services/post_service.py
    └── routers/post_router.py
```

mysite4와 달리 **모델(`models/`)과 스키마(`schemas/`)가 분리**됩니다. 모델은 DB 테이블, 스키마는 API 요청·응답 형식을 담당합니다.

## 준비

```bash
uv add sqlalchemy psycopg[binary] python-dotenv
```

| 라이브러리 | 역할 |
|------------|------|
| `sqlalchemy` | ORM 라이브러리 |
| `psycopg[binary]` | PostgreSQL 드라이버 |
| `python-dotenv` | `.env`에서 접속 정보 읽기 |

```sql
CREATE DATABASE mysite;
```

```
# fastapi_basic/.env
DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/mysite
```

`postgresql+psycopg`는 **DB 종류 + 드라이버**를 함께 지정하는 형식입니다. 비밀번호가 들어가므로 `.env`는 커밋하지 않습니다.

---

## DB 연결의 핵심 개념

| 개념 | 설명 |
|------|------|
| **Engine** | DB 연결과 SQL 실행을 관리하는 객체. `DATABASE_URL`로 연결할 DB와 드라이버를 지정 |
| **연결 풀** (Connection Pool) | DB 연결을 보관했다가 재사용하는 공간. 작업마다 연결을 새로 만드는 비용을 줄인다 |
| **세션** (Session) | DB 작업을 수행하고 파이썬 객체의 변경 사항을 추적하는 객체. 코드의 `db: Session`의 `db` |
| **Base** | `DeclarativeBase`를 상속한 모델의 기반. `class Post(Base)`처럼 선언한 모델의 테이블 정보가 `Base.metadata`에 모인다 |

**요청마다 세션을 하나 만들고**, Router → Service → Repository에 **같은 세션을 전달**합니다.

### database.py

```python
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv(Path(__file__).with_name(".env"))   # 실행 위치와 상관없이 같은 폴더의 .env
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(".env 파일에 DATABASE_URL을 설정하세요.")

engine = create_engine(DATABASE_URL)           # 연결 풀을 가진 Engine (앱 전체에 하나)
SessionLocal = sessionmaker(bind=engine)       # 세션을 찍어내는 공장


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()       # 요청마다 새 세션
    try:
        yield db              # 세션을 전달하고 여기서 멈춤 → 요청 처리
    finally:
        db.close()            # 요청이 끝나면(예외가 나도) 세션을 닫는다
```

## SQLAlchemy 모델

모델은 **파이썬 클래스 ↔ DB 테이블**을 연결합니다. `Post` 클래스는 `posts` 테이블에, `Post` 객체 하나는 게시글 한 행에 대응합니다.

```python
# mysite_db/models/post.py
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
```

- `Mapped[T]`: 속성의 **파이썬 타입**
- `mapped_column()`: **DB 컬럼**의 자료형과 제약 조건

| 설정 | 의미 |
|------|------|
| `primary_key=True` | 기본키 |
| `autoincrement=True` | 숫자 기본키 자동 생성 (mysite4에서 Repository가 하던 id 부여를 DB가 대신함) |
| `String(50)` | 최대 50자의 문자열 |
| `Text` | 긴 텍스트 |
| `nullable=False` | NULL 허용 안 함 |

```python
# mysite_db/models/__init__.py
from .post import Post      # 새 모델을 만들면 여기에 추가
```

## 테이블 생성과 lifespan

`main.py`에서 `models`를 import해야 모델 클래스가 실행되어 테이블 정보가 `Base.metadata`에 **등록**됩니다. import하지 않으면 `create_all()`이 만들 테이블을 모릅니다.

**lifespan**은 애플리케이션 **시작·종료 시** 실행할 코드를 작성하는 곳입니다.

```python
# main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import Base, engine
from mysite_db import models          # 사용하지 않아 보여도 등록을 위해 필요
from mysite_db.routers.post_router import router as db_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)   # 시작: 없는 테이블 생성
        yield                                    # 서버가 요청을 처리하는 동안
    finally:
        engine.dispose()                         # 종료: 연결 풀 정리


app = FastAPI(lifespan=lifespan)
app.include_router(db_router)
```

- `create_all()`은 **없는 테이블만 생성**한다. 이미 있는 테이블의 구조(컬럼 추가 등)는 바꾸지 않는다 → 구조 변경은 Alembic 같은 마이그레이션 도구가 필요
- 실제 `main.py`에는 mysite~mysite4 라우터도 함께 등록되어 있다

| | lifespan | get_db() |
|---|----------|----------|
| 범위 | 애플리케이션 전체 | 요청 하나 |
| `yield` 전 | 테이블 준비 | 세션 생성 |
| `yield` 후 (`finally`) | `engine.dispose()` 연결 풀 정리 | `db.close()` 세션 닫기 |

---

## 의존성 주입 (Dependency Injection)

Router가 Service를 호출하려면 **세션**이 필요합니다. 이렇게 기능 실행에 필요한 객체를 **의존성**이라 하고, 이를 **외부에서 준비해 함수에 전달**하는 방식을 **의존성 주입**이라 합니다. 여기서는 FastAPI가 `get_db()`로 세션을 준비해 Router에 넣어 줍니다.

```python
db: Annotated[Session, Depends(get_db)]
```

| 코드 | 의미 |
|------|------|
| `db` | 세션을 전달받는 매개변수 |
| `Session` | 전달받을 객체의 **타입**. 이 선언만으로 세션이 생성되지는 않음 |
| `Depends(get_db)` | FastAPI가 `get_db`를 실행해 `yield`한 값을 넣도록 지정. **괄호 없이 함수 자체**를 전달 |
| `Annotated[타입, 추가정보]` | 타입에 추가 정보(여기선 `Depends`)를 붙이는 문법 |

각 Router에서 `SessionLocal()` + `try/finally`를 직접 쓰는 것과 비교한 장점:

- **중복 감소**: 세션 생성·종료를 `get_db()` 한곳에서 관리 → 반복 코드와 `close()` 누락을 줄인다
- **역할 분리**: Router는 세션을 어떻게 만드는지 몰라도 받은 `db`로 Service만 호출
- **테스트 편의**: `app.dependency_overrides`로 `get_db`를 테스트용 세션 함수로 교체 가능

### Router

```python
router = APIRouter(prefix="/posts-db", tags=["mysite_db"])


@router.post("", response_model=PostDetailResponse, status_code=status.HTTP_201_CREATED)
def create_post(data: PostCreate, db: Annotated[Session, Depends(get_db)]):
    return post_service.create_post(db, data)


@router.get("", response_model=list[PostListResponse])
def get_posts(db: Annotated[Session, Depends(get_db)]):
    return post_service.get_posts(db)


@router.get("/{id}", response_model=PostDetailResponse)
def get_post(id: int, db: Annotated[Session, Depends(get_db)]):
    return post_service.get_post(db, id)


@router.put("/{id}", response_model=PostDetailResponse)
def update_post(id: int, data: PostCreate, db: Annotated[Session, Depends(get_db)]):
    return post_service.update_post(db, id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(id: int, db: Annotated[Session, Depends(get_db)]):
    post_service.delete_post(db, id)
```

`data: PostCreate`는 **클라이언트가 보낸** 요청 본문, `db`는 **서버가 준비한** 세션입니다. 클라이언트는 세션을 보내지 않습니다.

## Pydantic 스키마

```python
class PostCreate(BaseModel):            # 등록·수정 요청
    title: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)


class PostDetailResponse(BaseModel):
    id: int
    title: str
    content: str

    model_config = ConfigDict(from_attributes=True)


class PostListResponse(BaseModel):
    id: int
    title: str

    model_config = ConfigDict(from_attributes=True)
```

- mysite4에서 Service가 하던 **빈 문자열 검사를 `Field`로 Pydantic에 위임** → Service는 존재 확인과 트랜잭션에 집중
- `max_length=50`은 모델의 `String(50)`과 맞춘 값. 맞추지 않으면 51자 이상이 DB 오류(500)로 터진다
- `from_attributes=True`: dict가 아닌 **SQLAlchemy 객체의 속성**(`post.id`, `post.title`)에서 응답 필드를 읽도록 설정

## Service — 트랜잭션 관리

```python
class PostService:
    def create_post(self, db: Session, data: PostCreate):
        with db.begin():
            new_post = Post(title=data.title, content=data.content)
            post_repository.save(db, new_post)

        return new_post

    def get_posts(self, db: Session):
        return post_repository.find_all(db)

    def get_post(self, db: Session, id: int):
        post = post_repository.find_by_id(db, id)
        if post is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="게시글을 찾을 수 없습니다.")
        return post

    def update_post(self, db: Session, id: int, data: PostCreate):
        with db.begin():
            post = self.get_post(db, id)
            updated_post = post_repository.update(db, post, data)

        return updated_post

    def delete_post(self, db: Session, id: int):
        with db.begin():
            post = self.get_post(db, id)
            post_repository.delete(db, post)
```

등록·수정·삭제는 각각 `with db.begin():` 블록 = **하나의 트랜잭션**입니다.

- 블록이 정상 종료 → 자동 **commit**
- 블록 안이나 commit 중 예외 → 자동 **rollback** 후 예외를 다시 던짐 (없는 ID면 404 `HTTPException`이 나가면서 rollback)
- 같은 블록에서 같은 세션으로 Repository를 여러 번 호출해도 변경은 **함께 확정되거나 함께 취소**된다
- 등록·수정은 블록이 끝나 **commit을 마친 뒤** 객체를 반환한다
- 조회도 트랜잭션을 **자동으로 시작**하므로, 수정·삭제 대상 조회는 `with db.begin():` **안에** 둔다. 밖에서 먼저 조회하면 이미 시작된 트랜잭션 때문에 `begin()`이 오류를 낸다

> 트랜잭션 경계(언제 확정할지)는 **업무 규칙**이므로 Repository가 아니라 Service가 정한다.

## Repository — 세션으로 CRUD

```python
class PostRepository:
    def save(self, db: Session, new_post: Post):
        db.add(new_post)
        return new_post

    def find_all(self, db: Session):
        return db.scalars(select(Post).order_by(Post.id)).all()

    def find_by_id(self, db: Session, id: int):
        return db.get(Post, id)             # 없으면 None

    def update(self, db: Session, post: Post, data: PostCreate):
        post.title = data.title             # 속성만 변경 (변경 감지)
        post.content = data.content
        return post

    def delete(self, db: Session, post: Post):
        db.delete(post)
```

mysite4와 비교하면 리스트·ID 카운터가 사라지고 **모든 메서드가 `db`를 첫 인자로** 받습니다. Repository는 commit하지 않고 세션에 작업만 등록합니다.

## 변경 감지 (Dirty Checking)

`db.get(Post, id)`로 조회한 `post`는 **세션이 관리하는 객체**입니다. 속성만 바꿔도 세션이 변경을 추적하므로 `db.add()`를 다시 하거나 UPDATE문을 직접 쓸 필요가 없습니다.

| 단계 | 동작 |
|------|------|
| 속성 변경 | 파이썬 객체의 값을 바꾸고, 세션이 변경을 추적 |
| flush | 변경 사항을 UPDATE SQL로 실행. 아직 확정 아님 |
| commit | 트랜잭션 확정 → 저장 |

`with db.begin():` 블록이 끝날 때의 commit에 **flush가 포함**되므로, Repository에서 속성만 바꿔도 DB에 저장됩니다.

## mysite4 → mysite_db 변경 정리

| 항목 | mysite4 (메모리) | mysite_db (PostgreSQL) |
|------|------------------|------------------------|
| 저장소 | `self.posts` 리스트 | `posts` 테이블 |
| id 부여 | Repository의 카운터 | DB `autoincrement` |
| 게시글 객체 | 일반 클래스 `Post` | SQLAlchemy 모델 `Post(Base)` |
| 빈 문자열 검증 | Service | Pydantic `Field(min_length=1)` |
| 세션 | 없음 | `get_db()` + `Depends`로 요청마다 주입 |
| 확정 | 즉시 반영 | Service의 `with db.begin():` commit |
| 수정 | 리스트에서 찾아 값 변경 | 변경 감지 |
| 재시작 후 | 데이터 사라짐 | **데이터 유지** |

## 실행 확인

```bash
uv run fastapi dev main.py
```

PostgreSQL 실행 + `.env` 설정 후, `http://127.0.0.1:8000/docs`의 `mysite_db` 그룹에서 확인합니다.

```json
{
  "title": "첫 번째 게시글",
  "content": "데이터베이스에 저장할 내용입니다."
}
```

1. 위 데이터로 등록 → 201
2. **서버를 재시작**한 뒤 목록·상세 조회 → 그대로 조회됨
3. 수정 → 상세 조회에서 변경 내용 확인
4. 삭제 → 204, 이후 상세 조회 → 404
