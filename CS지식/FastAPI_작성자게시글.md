# FastAPI 작성자가 있는 게시글 — 인증과 인가 적용

[FastAPI JWT 회원가입과 로그인](FastAPI_JWT회원가입로그인.md)의 `mysite_auth`에 게시글을 추가해, **로그인한 사용자를 작성자로 저장**하고 **수정·삭제는 작성자 본인만** 할 수 있게 만듭니다. 개념은 [인증과 인가](인증과인가.md), 계층 구조는 [FastAPI 레이어드 아키텍처](FastAPI_레이어드아키텍처.md), 즉시 로딩은 [SQLAlchemy N+1 문제](SQLAlchemy_N+1문제.md)를 참고하세요.

## API

| 메서드 | 경로 | 기능 | 인증 | 성공 |
|--------|------|------|------|------|
| POST | `/posts-auth` | 게시글 작성 | 필요 | 201 |
| GET | `/posts-auth` | 전체 목록 조회 | 불필요 | 200 |
| GET | `/posts-auth/{post_id}` | 상세 조회 | 불필요 | 200 |
| PUT | `/posts-auth/{post_id}` | 게시글 수정 | **작성자 본인** | 200 |
| DELETE | `/posts-auth/{post_id}` | 게시글 삭제 | **작성자 본인** | 204 |
| GET | `/me/posts` | 내가 쓴 글 조회 | 필요 | 200 |
| GET | `/users/{user_id}/posts` | 특정 사용자의 글 조회 | 불필요 | 200 |

## 모델과 스키마

### 게시글 모델

`user_id`는 작성자의 **외래 키**, `user`는 작성자 객체에 접근하는 **관계 속성**이다.

```python
class PostAuth(Base):
    __tablename__ = "post_auth"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_auth.id"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="posts")
```

### 사용자 모델

`User.posts`와 `PostAuth.user`를 `back_populates`로 **서로 연결**한다. (1:N — 사용자 1, 게시글 N, FK는 N쪽인 `post_auth.user_id`)

```python
# mysite_auth/models/user.py (추가분)
posts: Mapped[list["PostAuth"]] = relationship(back_populates="user")
```

- 두 모델이 서로를 import하면 순환 참조가 되므로 `if TYPE_CHECKING:` 안에서만 import하고, 관계 타입은 문자열(`"User"`, `"PostAuth"`)로 쓴다.
- 모델은 `mysite_auth/models/__init__.py`에서 함께 등록해, 테이블 생성 시 모두 인식되게 한다.

### 요청·응답 스키마

```python
class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)

class PostListResponse(BaseModel):
    id: int
    title: str
    user: UserResponse

    model_config = ConfigDict(from_attributes=True)

class PostDetailResponse(BaseModel):
    id: int
    title: str
    content: str
    user: UserResponse

    model_config = ConfigDict(from_attributes=True)
```

- **요청에는 제목과 내용만** 받는다. 작성자는 요청 본문이 아니라 **인증된 사용자의 `current_user.id`**로 정한다. (클라이언트가 보낸 값으로 작성자를 속일 수 없다)
- 응답의 작성자 정보는 비밀번호가 빠진 `UserResponse`를 쓴다.

## Repository와 Service

### Repository

`joinedload(PostAuth.user)`로 **게시글과 작성자를 한 번에** 조회한다. 응답 변환 때 작성자를 읽으면서 생기는 N+1을 막는다.

```python
def find_all(self, db: Session):
    return db.scalars(
        select(PostAuth).options(joinedload(PostAuth.user)).order_by(PostAuth.id)
    ).all()

def find_by_user_id(self, db: Session, user_id: int):
    return db.scalars(
        select(PostAuth)
        .options(joinedload(PostAuth.user))
        .where(PostAuth.user_id == user_id)
        .order_by(PostAuth.id)
    ).all()
```

`find_by_id`, `save`, `update`, `delete`도 같은 방식이며, `update`는 제목·내용만 바꾼다.

### Service

수정·삭제 시 `post.user_id`와 `current_user.id`를 비교해 **작성자 본인인지 확인**한다.

```python
def update_post(self, db, post_id, data, current_user):
    with db.begin():
        post = self.get_post(db, post_id)
        if post.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="본인의 게시글만 수정할 수 있습니다.",
            )
        updated_post = post_repository.update(db, post, data)
    return updated_post
```

- 작성은 `PostAuth(title=..., content=..., user_id=current_user.id)`로 만든다.
- 게시글이 없으면 `get_post`에서 **404**를 낸다. 삭제도 같은 구조로 403 검사 후 `delete`한다.
- 조회(존재 확인)와 소유자 비교, 수정이 **같은 트랜잭션** 안에서 일어난다.

### 인증과 인가의 위치

| 구분 | 확인하는 내용 | 처리 위치 | 실패 응답 |
|------|---------------|-----------|-----------|
| 인증 (Authentication) | 유효한 토큰을 가진 사용자인가? | `Depends(get_current_user)` | **401** |
| 인가 (Authorization) | 해당 게시글의 작성자인가? | Service의 `post.user_id != current_user.id` 검사 | **403** |

- 인증은 **누구인지**(라우터 앞 의존성), 인가는 **이 자원을 건드릴 권한이 있는지**(자원을 읽은 뒤 서비스에서)를 본다. 게시글을 읽어야 작성자를 알 수 있으므로 인가는 서비스 계층에서 한다.

## Router

### 게시글 라우터

`Depends(get_db)`로 DB 세션을 받고, **인증이 필요한 작업에만** `Depends(get_current_user)`를 추가한다.

```python
router = APIRouter(prefix="/posts-auth", tags=["mysite_auth"])

@router.post("", response_model=PostDetailResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    data: PostCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    return post_service.create_post(db, data, current_user)

@router.get("", response_model=list[PostListResponse])
def get_posts(db: Annotated[Session, Depends(get_db)]):          # 인증 불필요
    return post_service.get_posts(db)

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: ..., current_user: ...):
    post_service.delete_post(db, post_id, current_user)
```

- 목록(`PostListResponse`)에는 `content`가 없고, 상세(`PostDetailResponse`)에만 있다.
- 삭제는 **204**로 본문 없이 응답한다.

### 사용자 라우터

```python
@router.get("/me/posts", response_model=list[PostListResponse])
def get_my_posts(db, current_user):
    return post_service.get_posts_by_user_id(db, current_user.id)

@router.get("/users/{user_id}/posts", response_model=list[PostListResponse])
def get_posts_by_user(user_id: int, db):
    return post_service.get_posts_by_user_id(db, user_id)
```

- `/me/posts`는 **인증된 사용자 ID**, `/users/{user_id}/posts`는 **URL의 사용자 ID**로 조회한다. 같은 Service 함수를 재사용한다.

### 공통 서버에 등록

```python
# main.py
from mysite_auth import models as auth_models
from mysite_auth.routers.auth_router import router as auth_router
from mysite_auth.routers.post_router import router as auth_post_router
from mysite_auth.routers.user_router import router as user_router

app.include_router(auth_router)
app.include_router(auth_post_router)
app.include_router(user_router)
```

## 권한 확인

1. 로그인 후 토큰을 **Authorize**에 입력하고 `POST /posts-auth`로 글을 쓴다.
   ```json
   {"title": "작성자가 있는 게시글", "content": "로그인한 사용자가 작성자로 저장됩니다."}
   ```
2. 응답의 `user.id`가 로그인한 사용자의 ID인지 확인한다.
3. `/me/posts`에 **본인이 쓴 글만** 나오는지 확인한다.
4. **다른 계정**으로 로그인해 수정·삭제하면 **403**인지 확인한다.
5. **토큰 없이** 작성·수정·삭제하면 **401**인지 확인한다.

## 정리

- 작성자는 **요청 본문이 아니라 인증된 사용자**에서 가져와 저장한다.
- 인증(401)은 라우터 의존성에서, 인가(403)는 서비스에서 `post.user_id != current_user.id`로 판단한다.
- 조회 API는 인증 없이 열고, 쓰기 API만 `Depends(get_current_user)`로 보호한다.
- 1:N 관계(사용자-게시글)는 FK(`user_id`) + `relationship(back_populates)`로 양방향 연결하고, 목록 조회에는 `joinedload`로 N+1을 피한다.
