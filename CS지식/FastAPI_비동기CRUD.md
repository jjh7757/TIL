# FastAPI 비동기 CRUD

[비동기 설정과 Alembic](FastAPI_비동기설정_Alembic.md)에서 만든 `AsyncSession`으로 `fastapi_agent`의 CRUD를 비동기로 호출하고, 비동기 환경에 맞게 **관계 로딩**을 설정합니다.

## 비동기 ORM의 관계 로딩

### 왜 lazy loading이 안 되는가

`AsyncSession`에서는 `post.user` 같은 **일반 속성 접근**으로 생긴 DB I/O를 `await`할 수 없습니다. 속성 접근은 `await`를 붙일 수 없는 동기 동작이기 때문입니다. 그래서 지연 로딩이 일어나면 `MissingGreenlet` 오류가 날 수 있습니다.

응답 모델 변환·직렬화도 관계 속성을 **동기적으로** 읽으므로, 응답에 필요한 관계는 **미리 로딩**해야 합니다. 비동기에서도 `joinedload()`/`selectinload()`를 적용한 조회를 `await db.scalar(...)`/`await db.scalars(...)`하면, 그 `await`가 끝날 때 지정한 관계까지 로딩됩니다. ([N+1 문제](SQLAlchemy_N+1문제.md)의 즉시 로딩과 같은 방법)

### `lazy="raise"` — 암묵적 조회 금지

```python
# domains/posts/models.py (Post 클래스 발췌)
user: Mapped["User"] = relationship(back_populates="posts", lazy="raise")
```

| 상황 | 결과 |
|------|------|
| 로딩하지 않은 관계에 접근 | SQL 실행 대신 즉시 `InvalidRequestError` |
| 이미 로딩한 관계에 접근 | 일반 속성처럼 읽힘 |

`MissingGreenlet`은 어디서 터졌는지 알기 어렵지만, `lazy="raise"`는 **"이 관계를 미리 로딩하지 않았다"** 는 사실을 명확한 오류로 알려 줍니다. 동기 환경에서도 N+1을 개발 중에 바로 발견하는 용도로 쓸 수 있습니다.

### 예시: 게시글 생성 후 작성자 정보 반환

`Post(user_id=current_user.id)`로 만들면 **작성자 ID만** 지정한 것이고 `post.user`가 로딩된 것은 아닙니다.

- 동기 세션: 응답 모델이 `post.user`를 읽을 때 지연 로딩으로 가져올 수 있음
- 비동기 세션: 그 조회를 기다릴 수 없으므로 **응답 전에 준비**해야 함

| 방법 | 코드 |
|------|------|
| 관계를 로딩하는 조회로 다시 불러오기 | `joinedload(Post.user)`를 적용한 조회를 `await` |
| 특정 관계만 새로고침 | `await db.refresh(post, ["user"])` |

## 비동기 CRUD 호출

### 호출 흐름

```
Router → await Service → await Repository → await DB I/O
```

중간 계층 하나라도 `await`를 빠뜨리면 결과 대신 **코루틴 객체**가 반환됩니다.

### `await`를 붙이는 것 / 붙이지 않는 것

| 작업 | 코드 | `await` |
|------|------|---------|
| 객체 등록 | `db.add(post)` | ✗ (세션에 등록만, I/O 없음) |
| 속성 변경 | `post.title = data.title` | ✗ |
| flush | `await db.flush()` | ○ |
| 단일 조회 | `await db.scalar(...)`, `await db.get(...)` | ○ |
| 목록 조회 | `await db.scalars(...)` | ○ |
| 버퍼링된 결과 읽기 | `result.all()` | ✗ (이미 받아 온 결과) |
| 삭제 등록 | `await db.delete(post)` | ○ (관계 처리 중 DB I/O가 필요할 수 있음) |

> 기준: **DB와 통신할 수 있는 작업**에만 `await`. 동기 `delete()`는 I/O가 없었지만 비동기에서는 `await`가 필요한 점에 주의.

### Repository

```python
# domains/posts/repository.py (PostRepository 발췌)
async def save(self, db: AsyncSession, post: Post) -> Post:
    db.add(post)
    await db.flush()          # INSERT 실행 → post.id 확보
    return post


async def find_by_id(self, db: AsyncSession, post_id: int) -> Post | None:
    return await db.scalar(
        select(Post)
        .options(
            joinedload(Post.user),                                 # 게시글 작성자 (N:1)
            selectinload(Post.comments).joinedload(Comment.user),  # 댓글 (1:N) → 댓글 작성자 (N:1)
        )
        .where(Post.id == post_id)
    )
```

상세 응답에 필요한 **작성자, 댓글, 댓글 작성자**를 조회 한 번(SQL 2회)으로 모두 준비합니다.

### Service — `async with db.begin()`

```python
# domains/posts/service.py (PostService 발췌)
async def create_post(
    self, db: AsyncSession, data: PostCreate, current_user: UserResponse
) -> Post:
    async with db.begin():
        post = Post(
            title=data.title,
            content=data.content,
            user_id=current_user.id,
            comments=[],               # 새 글은 댓글이 없음 → 빈 목록으로 "로딩된 상태"로 둠
        )
        await post_repository.save(db, post)      # flush로 post.id 확보
        result = await self.get_post(db, post.id) # 관계까지 로딩된 상세 조회
    return result
```

- 트랜잭션 블록은 `async with db.begin()` (정상 종료 시 commit, 예외 시 rollback은 동기와 동일)
- `save()`의 flush로 id를 얻은 뒤, 같은 트랜잭션에서 **관계를 로딩하는 상세 조회**를 `await`해 응답 준비

### Router

```python
# domains/posts/router.py (발췌)
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    posts = await post_service.get_posts(db)
    return SuccessResponse[list[PostListResponse]](data=posts)
```

핸들러를 `async def`로 선언하고 `AsyncSession`을 주입받아 Service를 `await`합니다. (`SuccessResponse`는 [공통 응답과 예외 처리](FastAPI_공통응답_예외처리.md) 참고)

### 인증 조회

```python
# core/dependencies.py (get_current_user 내부 발췌)
async with SessionLocal() as db:
    user = await user_service.get_current_user(db, credentials.credentials)
    return UserResponse.model_validate(user)
```

인증 의존성에서도 세션은 `async with`로 열고 비동기 Service는 `await`로 호출합니다. 세션 안에서 **DTO로 바꿔 반환**하므로 세션이 닫힌 뒤 ORM 객체를 쓰는 문제가 없습니다.

## 비동기 함수 안의 동기 연산

비밀번호 해싱·검증(Argon2)은 **CPU를 많이 쓰는 동기 연산**입니다. 비동기 Service에서 그대로 실행하면 그동안 **이벤트 루프를 점유**해 다른 요청이 멈춥니다. `run_in_threadpool()`로 별도 스레드에서 실행하고 완료를 기다립니다.

```python
from starlette.concurrency import run_in_threadpool

# 비동기 함수 내부
hashed_password = await run_in_threadpool(hash_password, data.password)
valid = await run_in_threadpool(verify_password, data.password, user.hashed_password)
```

`run_in_threadpool(함수, *인자)` — 함수를 **호출하지 않고 함수 자체와 인자를 따로** 넘깁니다. `run_in_threadpool(hash_password(data.password))`처럼 쓰면 현재 스레드에서 이미 실행되어 버립니다.

| 작업 종류 | 비동기 함수 안에서 |
|-----------|-------------------|
| 비동기 I/O (AsyncSession, 비동기 HTTP 클라이언트) | `await` |
| 동기 I/O / 무거운 CPU 연산 (해싱 등) | `await run_in_threadpool(...)` |
| 가벼운 연산 (객체 생성, 속성 변경) | 그대로 실행 |
