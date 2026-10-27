# SQLAlchemy N+1 문제와 즉시 로딩

[FastAPI 다대다 관계](FastAPI_다대다관계.md)처럼 `relationship()`으로 모델을 연결하면, 연관 데이터를 읽을 때마다 SQL이 몰래 실행될 수 있습니다. 관련 코드는 `fastapi_basic/mysite_nplusone/`에 있습니다.

## N+1 문제

목록을 **한 번** 조회한 뒤, 각 항목의 연관 데이터를 가져오려고 **항목마다 개별 조회**를 반복하는 문제입니다.

게시글 N개와 각 게시글의 댓글을 조회하면:

- 게시글 목록 조회: **1회**
- 게시글마다 댓글 목록 조회: **N회**
- 합계: **1 + N회**

목록이 커질수록 DB 왕복과 쿼리 처리 시간이 누적되어 응답이 느려집니다.

## 실습 모델

```
user_nplusone (사용자)
   │ 1:N              │ 1:N
   ▼                  ▼
post_nplusone ──1:N──▶ comment_nplusone
(게시글, user_id FK)   (댓글, post_id FK, user_id FK)
```

```python
class UserNPlusOne(Base):
    __tablename__ = "user_nplusone"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    posts: Mapped[list["PostNPlusOne"]] = relationship(
        "PostNPlusOne", back_populates="user", order_by="PostNPlusOne.id")
    comments: Mapped[list["CommentNPlusOne"]] = relationship(
        "CommentNPlusOne", back_populates="user", order_by="CommentNPlusOne.id")


class PostNPlusOne(Base):
    __tablename__ = "post_nplusone"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_nplusone.id"), nullable=False)

    user: Mapped["UserNPlusOne"] = relationship("UserNPlusOne", back_populates="posts")
    comments: Mapped[list["CommentNPlusOne"]] = relationship(
        "CommentNPlusOne", back_populates="post", order_by="CommentNPlusOne.id")


class CommentNPlusOne(Base):
    __tablename__ = "comment_nplusone"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(String(200), nullable=False)
    post_id: Mapped[int] = mapped_column(ForeignKey("post_nplusone.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_nplusone.id"), nullable=False)

    post: Mapped["PostNPlusOne"] = relationship("PostNPlusOne", back_populates="comments")
    user: Mapped["UserNPlusOne"] = relationship("UserNPlusOne", back_populates="comments")
```

- `ForeignKey`는 테이블 사이 연결, `relationship()`은 연결된 ORM 객체에 접근할 속성, `back_populates`는 양쪽 관계 속성 연결
- 각 파일은 `if TYPE_CHECKING:` 안에서만 서로를 import한다 → 타입 힌트용으로만 쓰고 **실행 시 순환 import를 피함**. `relationship("PostNPlusOne")`처럼 문자열로 지정하므로 실행 중엔 import가 필요 없다

## 지연 로딩 (Lazy Loading)

연관 데이터를 **실제로 사용하는 시점까지 조회를 미루는** 방식입니다. `relationship()`의 **기본값**입니다.

```python
posts = db.scalars(select(PostNPlusOne)).all()   # 게시글 SQL 1회

for post in posts:
    print(post.comments)    # 아직 안 불러온 댓글 → 게시글마다 SELECT 추가 실행
```

이 댓글 조회가 게시글마다 반복되어 **N+1**이 됩니다. 코드에는 SQL이 보이지 않아 놓치기 쉽습니다. FastAPI에서는 **응답 DTO로 변환**하면서(`response_model`이 `post.comments`를 읽으면서) 발생하기도 합니다.

## 즉시 로딩 (Eager Loading)

조회 결과를 가져오면서 **필요한 연관 데이터도 미리 준비**하는 방식입니다. 조회문의 `.options()`에 로딩 전략을 지정합니다.

### joinedload — JOIN으로 한 번에

```python
stmt = (
    select(PostNPlusOne)
    .options(joinedload(PostNPlusOne.user))
    .order_by(PostNPlusOne.id)
)
posts = db.scalars(stmt).all()
```
```sql
SELECT p.id, p.title, p.user_id,
       u.id AS loaded_user_id, u.name AS user_name
FROM post_nplusone AS p
LEFT OUTER JOIN user_nplusone AS u ON u.id = p.user_id
ORDER BY p.id;
```

이후 `post.user.name`을 읽어도 추가 SQL이 없습니다.

**1:N 컬렉션**에 쓰면 댓글 수만큼 게시글 컬럼이 반복됩니다.

```python
stmt = (
    select(PostNPlusOne)
    .options(joinedload(PostNPlusOne.comments))
    .order_by(PostNPlusOne.id)
)
posts = db.scalars(stmt).unique().all()     # .unique() 필수
```
```sql
SELECT p.id, p.title, p.user_id,
       c.id AS comment_id, c.content, c.post_id, c.user_id
FROM post_nplusone AS p
LEFT OUTER JOIN comment_nplusone AS c ON c.post_id = p.id
ORDER BY p.id, c.id;
```

- JOIN 결과 행마다 같은 게시글 객체가 나오므로 **`.unique()`로 중복 제거**해야 한다. 생략하면 예외 발생
- `.unique()`는 파이썬 쪽 중복 제거일 뿐, **DB에서 가져오는 행 수는 줄지 않는다** (게시글 25 × 댓글 5 = 125행)

### selectinload — IN으로 따로

게시글을 먼저 조회한 뒤, **조회한 게시글 ID를 모아 `IN` 조건으로** 댓글을 가져옵니다.

```python
stmt = (
    select(PostNPlusOne)
    .options(selectinload(PostNPlusOne.comments))
    .order_by(PostNPlusOne.id)
)
posts = db.scalars(stmt).all()
```
```sql
SELECT p.id, p.title, p.user_id
FROM post_nplusone AS p
ORDER BY p.id;

SELECT c.id, c.content, c.post_id, c.user_id
FROM comment_nplusone AS c
WHERE c.post_id IN (1, 2, 3, ..., 25)
ORDER BY c.id;
```

- 댓글은 `post_id`에 따라 각 게시글의 `comments`에 채워진다. `.all()` 시점에 댓글까지 준비 완료
- 보통 **SQL 2회**. 게시글이 없으면 댓글 조회 생략, 게시글이 아주 많으면 ID를 나눠 조회해 횟수가 늘 수 있음

### 선택 기준

| 관계 | 우선 고려 | 이유 |
|------|-----------|------|
| N:1, 1:1 | `joinedload` | 연결된 객체 **하나**를 JOIN으로 가져오기 좋다 |
| 1:N, M:N | `selectinload` | JOIN하면 부모 데이터가 자식 수만큼 **반복**된다 |

둘 다 단일 객체·컬렉션 모두에 쓸 수 있습니다. SQL 횟수뿐 아니라 **가져오는 데이터 양**도 고려하고, **응답에 필요한 관계만** 로딩합니다.

## 복합 관계에서의 즉시 로딩

### 여러 관계를 함께 — `.options()`에 나열

```python
stmt = (
    select(PostNPlusOne)
    .options(
        joinedload(PostNPlusOne.user),          # 게시글 작성자: N:1 → JOIN
        selectinload(PostNPlusOne.comments),    # 댓글: 1:N → IN
    )
    .order_by(PostNPlusOne.id)
)
```

게시글+작성자 JOIN 1회, 댓글 IN 1회 → **총 2회**.

### 관계를 따라 이어서 — 체이닝

게시글 → 댓글 → **댓글 작성자**까지 필요하면 경로를 따라 옵션을 연결합니다.

```python
stmt = (
    select(PostNPlusOne)
    .options(
        selectinload(PostNPlusOne.comments).joinedload(CommentNPlusOne.user)
    )
    .order_by(PostNPlusOne.id)
)
```
```sql
SELECT p.id, p.title, p.user_id FROM post_nplusone AS p ORDER BY p.id;

SELECT c.id, c.content, c.post_id, c.user_id,
       u.id AS loaded_user_id, u.name AS user_name
FROM comment_nplusone AS c
LEFT OUTER JOIN user_nplusone AS u ON u.id = c.user_id
WHERE c.post_id IN (1, 2, ..., 25)
ORDER BY c.id;
```

게시글→댓글은 1:N이라 `selectinload`, 댓글→작성자는 N:1이라 `joinedload`. 댓글을 가져오는 SQL에서 작성자까지 JOIN하므로 **총 2회**, 이후 `comment.user.name`도 추가 조회 없음.

## 일반 `join()` vs `joinedload()`

```python
stmt = (
    select(PostNPlusOne)
    .join(PostNPlusOne.user)
    .where(UserNPlusOne.name == "Alice")
)
```
```sql
SELECT p.id, p.title, p.user_id          -- 게시글 컬럼만
FROM post_nplusone AS p
JOIN user_nplusone AS u ON u.id = p.user_id
WHERE u.name = 'Alice';
```

| | `join()` | `joinedload()` |
|---|----------|----------------|
| 목적 | 연결 테이블 컬럼으로 **필터링·정렬** | 관계 객체를 **미리 채우기** |
| `post.user` | 채워지지 않음 → 읽으면 추가 SQL | 채워짐 |
| JOIN 종류 | INNER JOIN | 기본 LEFT OUTER JOIN |

필터링도 하고 관계 객체도 필요하면 `join()`에 로딩 옵션을 **함께** 추가합니다.

---

## 실습

### 준비

```python
engine = create_engine(DATABASE_URL, echo=True)   # 실행되는 SQL을 터미널에 출력
```

1. `/docs`의 `mysite_nplusone` 그룹에서 `POST /nplusone/setup`을 본문 없이 호출 → 사용자 5명, 게시글 25개, 댓글 125개 생성 (각 게시글에 사용자 5명이 댓글 하나씩). 다시 호출하면 지우고 재생성
2. 조회 API 응답에는 `echo` 없이도 다음이 포함된다

| 필드 | 내용 |
|------|------|
| `query_count` | 조회 + **응답 DTO 변환 중** 실행된 SQL 횟수 (지연 로딩 포함) |
| `queries` | 실행된 SQL 문장 목록 |
| `posts` | 조회한 게시글과 연관 데이터 |

### 결과 비교

| API | 로딩 방식 | SQL 횟수 | 내역 |
|-----|-----------|----------|------|
| `/posts/with-user` | 지연 | **6** | 게시글 1 + 작성자 5 |
| `/posts/with-user/optimized` | `joinedload(user)` | **1** | 게시글–사용자 LEFT OUTER JOIN |
| `/posts/with-comments` | 지연 | **26** | 게시글 1 + 댓글 25 |
| `/posts/with-comments/optimized` | `selectinload(comments)` | **2** | 게시글 + 댓글 `post_id IN (...)` |
| `/posts/with-comments/joined` | `joinedload(comments)` + `.unique()` | **1** | 게시글–댓글 JOIN (125행 → 게시글 25개) |
| `/posts/full` | 지연 | **31** | 게시글 1 + 작성자 5 + 댓글 25 |
| `/posts/full/optimized` | `joinedload(user)` + `selectinload(comments)` | **2** | 게시글–작성자 JOIN + 댓글 IN |
| `/posts/with-comment-users` | 지연 | **31** | 게시글 1 + 댓글 25 + 댓글 작성자 5 |
| `/posts/with-comment-users/optimized` | `selectinload(comments).joinedload(user)` | **2** | 게시글 + 댓글–작성자 JOIN을 IN으로 |

(모든 경로 앞에 `/nplusone` 생략)

확인 포인트:

- **작성자가 25회가 아니라 5회인 이유**: 같은 사용자는 세션의 **identity map**에 이미 있어 재사용된다. 처음 보는 사용자만 조회
- 개선 전후 `posts` 내용은 **같고**, 반복 SELECT만 사라진다
- `/with-comments/joined`(1회) vs `/optimized`(2회): 같은 데이터. **SQL 1회가 항상 더 빠른 것은 아니다** — JOIN은 게시글 컬럼을 125행에 반복해서 가져온다
- `/full/optimized`와 `/with-comment-users/optimized`는 둘 다 2회지만 **JOIN 대상이 다르다**: 전자는 게시글–작성자, 후자는 댓글–작성자. 응답에서 `user`가 들어 있는 위치(게시글 바로 아래 vs 댓글 아래)도 다르다
