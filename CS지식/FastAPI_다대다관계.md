# FastAPI 다대다(M:N) 관계 — 게시글과 태그

[FastAPI DB 연동](FastAPI_DB연동.md)의 게시판에 **태그**를 붙입니다. 게시글 하나에 태그 여러 개, 태그 하나도 여러 게시글에서 쓰이므로 **M:N 관계**입니다. 관련 코드는 `fastapi_basic/mysite_many_to_many/`에 있습니다.

## API 목록

| 메서드 | URL | 설명 | 성공 |
|--------|-----|------|------|
| POST | `/posts-mn` | 태그 없이 게시글 등록 | 201 |
| GET | `/posts-mn` | 게시글 목록 | 200 |
| POST | `/posts-mn/with-tags` | 태그와 함께 게시글 등록 | 201 |
| GET | `/posts-mn/{post_id}` | 태그 포함 상세 조회 | 200 |
| PUT | `/posts-mn/{post_id}` | 제목·내용 수정 | 200 |
| DELETE | `/posts-mn/{post_id}` | 게시글 + 그 게시글의 **태그 연결** 삭제 (태그는 유지) | 204 |
| POST | `/tags-mn` | 태그 등록 | 201 |
| GET | `/tags-mn` | 태그 목록 | 200 |
| POST | `/posts-mn/{post_id}/tags` | 게시글에 태그 연결 (없는 태그는 생성) | 201 |
| DELETE | `/posts-mn/{post_id}/tags/{tag_id}` | 게시글–태그 **연결만** 해제 | 204 |

## 연결 테이블로 M:N 표현하기

관계형 DB는 M:N을 직접 표현할 수 없어 **연결 테이블**을 둡니다. 연결 한 건마다 게시글 ID와 태그 ID를 한 행으로 저장합니다.

```
post_mn (게시글)          post_tag_mn (연결)            tag_mn (태그)
┌────┬───────┬───────┐   ┌────┬─────────┬────────┐   ┌────┬───────────┐
│ id │ title │content│   │ id │ post_id │ tag_id │   │ id │ name (UK) │
│ PK │       │       │1:N│ PK │   FK    │   FK   │N:1│ PK │           │
└────┴───────┴───────┘   └────┴─────────┴────────┘   └────┴───────────┘
```

| 역할 | 모델 | 테이블 |
|------|------|--------|
| 게시글 | `PostMN` | `post_mn` |
| 태그 | `TagMN` | `tag_mn` |
| 연결 | `PostTagMN` | `post_tag_mn` |

`PostMN : PostTagMN = 1:N`, `TagMN : PostTagMN = 1:N` 두 관계를 합쳐 **게시글 : 태그 = M:N**이 됩니다.

| post_id | tag_id |
|---------|--------|
| 1 | 1 |
| 1 | 2 |
| 2 | 1 |

→ 게시글 1에는 태그 1, 2가 연결되고, 태그 1은 게시글 1, 2에서 함께 쓰인다.

---

## SQLAlchemy 모델

### 연결 모델

```python
# models/post_tag_mn.py
class PostTagMN(Base):
    __tablename__ = "post_tag_mn"
    __table_args__ = (
        UniqueConstraint("post_id", "tag_id", name="uq_post_tag_mn_post_tag"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("post_mn.id"), nullable=False)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag_mn.id"), nullable=False)

    post: Mapped["PostMN"] = relationship("PostMN", back_populates="post_tags")
    tag: Mapped["TagMN"] = relationship("TagMN", back_populates="post_tags")
```

- `ForeignKey`: 테이블 사이 연결(DB 차원). `relationship()`: 연결된 **ORM 객체에 접근할 속성**(파이썬 차원)
- `back_populates`: 양쪽 관계 속성을 서로 연결 (`PostTagMN.post` ↔ `PostMN.post_tags`)

### 태그 모델

```python
# models/tag_mn.py
class TagMN(Base):
    __tablename__ = "tag_mn"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    post_tags: Mapped[list["PostTagMN"]] = relationship(
        "PostTagMN",
        back_populates="tag",
        cascade="all, delete-orphan",
        order_by="PostTagMN.id",
    )
```

같은 태그를 여러 게시글이 쓰면 `TagMN` **하나를 공유**하고, 게시글마다 별도의 `PostTagMN`으로 연결합니다.

### 게시글 모델

```python
# models/post_mn.py
from .post_tag_mn import PostTagMN      # creator에서 실제로 생성하므로 일반 import

class PostMN(Base):
    __tablename__ = "post_mn"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    post_tags: Mapped[list["PostTagMN"]] = relationship(
        "PostTagMN",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostTagMN.id",
    )
    tags: AssociationProxy[list["TagMN"]] = association_proxy(
        "post_tags", "tag", creator=lambda tag: PostTagMN(tag=tag)
    )
```

`post_tags`에는 태그가 아니라 **연결 객체 `PostTagMN`**이 담깁니다. 태그 자체는 `tags` 프록시로 다룹니다.

### cascade 옵션

| 값 | 의미 | 이 예제에서 |
|----|------|-------------|
| `save-update` (`all`에 포함) | 부모를 세션에 add하면 관계 속 객체도 함께 등록 | 게시글만 `save()`해도 연결 객체·새 태그가 함께 저장 |
| `delete` (`all`에 포함) | 부모 삭제 시 자식도 삭제 | 게시글 삭제 → 그 게시글의 `PostTagMN` 행 삭제 |
| `delete-orphan` | 부모 컬렉션에서 빠진(고아가 된) 자식 삭제 | `post.tags.remove(tag)` → 그 연결 행만 삭제 |

`PostTagMN.tag` 쪽에는 cascade가 없으므로 **연결이 지워져도 태그 행은 남습니다**.

### 중복 연결 방지

`post_id`, `tag_id` 각각은 여러 행에 나올 수 있지만 **두 값의 조합**은 고유해야 합니다.

| 제약 조건 | 막는 중복 |
|-----------|-----------|
| `TagMN.name`의 `unique=True` | 같은 이름의 태그 여러 개 생성 |
| `PostTagMN`의 `UniqueConstraint("post_id", "tag_id")` | 같은 게시글에 같은 태그를 여러 번 연결 |

두 컬럼을 묶는 제약은 컬럼 옵션이 아니라 `__table_args__`에 지정합니다.

## association_proxy — 연결 객체 건너뛰기

**프록시(Proxy)**는 실제 대상에 대한 접근·작업을 대신 처리하는 대리자입니다. `association_proxy`를 쓰면 연결 객체를 거치지 않고 `post.tags`로 태그를 다룹니다.

```python
tags = association_proxy(
    "post_tags",                              # target_collection
    "tag",                                    # attr
    creator=lambda tag: PostTagMN(tag=tag),
)
```

| 인자 | 넣는 값 | 이 예제 |
|------|---------|---------|
| `target_collection` (1번째) | 현재 모델에서 연결 객체를 담는 **관계 속성 이름** | `"post_tags"` → `PostMN.post_tags` |
| `attr` (2번째) | 연결 객체에서 읽거나 설정할 **속성 이름** | `"tag"` → `PostTagMN.tag` |
| `creator` | 추가할 값을 받아 **연결 객체를 반환**하는 함수 | `lambda tag: PostTagMN(tag=tag)` |

> 1·2번째 인자는 **속성 이름 문자열**이다. 클래스명이나 테이블명을 넣는 자리가 아니다.

```python
post.post_tags[0].tag   # 연결 객체를 거쳐 첫 번째 태그
post.tags[0]            # 같은 TagMN 객체

post.tags.append(tag)   # creator가 PostTagMN(tag=tag)를 만들어 post.post_tags에 추가
post.tags.remove(tag)   # 해당 PostTagMN을 post.post_tags에서 제거 → delete-orphan으로 삭제
```

조회할 때는 `creator`가 호출되지 않습니다. 추가할 때만 쓰입니다.

## 스키마

```python
# schemas/tag.py
class TagCreate(BaseModel):
    name: str

class TagResponse(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

# schemas/post.py
class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)

class PostCreateWithTags(PostCreate):
    tags: list[str] = Field(default_factory=list)      # 태그 "이름" 목록, 생략 가능

class PostDetailResponse(BaseModel):
    id: int
    title: str
    content: str
    tags: list[TagResponse] = Field(default_factory=list)  # PostMN.tags에서 읽은 id·name
    model_config = ConfigDict(from_attributes=True)

class PostListResponse(BaseModel):
    id: int
    title: str
    model_config = ConfigDict(from_attributes=True)
```

- **입력**의 `tags`는 `list[str]`(이름), **응답**의 `tags`는 `list[TagResponse]`(id + 이름)
- 가변 기본값(리스트)은 `= []` 대신 `Field(default_factory=list)`로 요청마다 새 리스트를 만든다

## Repository

```python
class TagRepository:
    def find_by_name(self, db: Session, name: str):
        return db.scalar(select(TagMN).where(TagMN.name == name))

    def find_by_names(self, db: Session, names: list[str]):
        if not names:
            return []                         # 빈 목록이면 DB 조회 생략
        return db.scalars(select(TagMN).where(TagMN.name.in_(names))).all()


class PostTagRepository:
    def exists(self, db: Session, post_id: int, tag_id: int):
        stmt = (
            select(PostTagMN.id)
            .where(PostTagMN.post_id == post_id, PostTagMN.tag_id == tag_id)
            .exists()
        )
        return db.scalar(select(stmt))        # SELECT EXISTS (...) → True/False
```

- `find_by_names()`: `IN` 조건으로 여러 이름을 **한 번에** 조회 (이름마다 조회하지 않음)
- `exists()`: 행을 가져오지 않고 **존재 여부만** 확인

## Service

### 태그 단독 등록

```python
def create_tag(self, db: Session, data: TagCreate):
    with db.begin():
        if tag_repository.find_by_name(db, data.name) is not None:
            raise HTTPException(status_code=400, detail="이미 존재하는 태그 이름입니다.")
        new_tag = TagMN(name=data.name)
        tag_repository.save(db, new_tag)
    return new_tag
```

### 기존 게시글에 태그 연결

```python
def add_tag_to_post(self, db: Session, post_id: int, data: TagCreate):
    with db.begin():
        post = self.get_post(db, post_id)                     # 없으면 404
        tag = tag_repository.find_by_name(db, data.name)
        if tag is None:
            tag = TagMN(name=data.name)                       # 없는 태그는 새로 생성
        elif post_tag_repository.exists(db, post.id, tag.id):
            raise HTTPException(status_code=400, detail="이미 이 게시글에 등록된 태그입니다.")

        post.tags.append(tag)
    return post
```

- 중복 연결 검사(`EXISTS`)는 **기존 태그일 때만**. 새 태그는 연결된 적이 없으니 필요 없다
- `append()`에 **객체**를 넘기므로 새 태그의 id를 미리 얻을(flush) 필요가 없다. 태그 생성과 연결이 같은 트랜잭션에서 저장된다

### 태그와 함께 게시글 등록

```python
def create_post_with_tags(self, db: Session, data: PostCreateWithTags):
    with db.begin():
        names = list(dict.fromkeys(data.tags))                # 순서 유지 + 중복 제거
        tags_by_name = {
            tag.name: tag for tag in tag_repository.find_by_names(db, names)
        }
        new_post = PostMN(title=data.title, content=data.content)

        for name in names:
            tag = tags_by_name.get(name)
            if tag is None:
                tag = TagMN(name=name)                        # 없는 태그만 생성
            new_post.tags.append(tag)

        post_repository.save(db, new_post)                    # 게시글만 add
    return new_post
```

- `dict.fromkeys()`: `set()`과 달리 **입력 순서를 유지**하며 중복 제거
- 기존 태그는 한 번의 `IN` 조회로 가져와 dict로 찾고, 없는 것만 생성
- `save-update` cascade 덕분에 `tag_repository.save()`를 따로 부르지 않아도 연결 객체·새 태그가 commit 시 함께 저장된다

### 연결 해제

```python
def remove_tag_from_post(self, db: Session, post_id: int, tag_id: int):
    with db.begin():
        post = self.get_post(db, post_id)
        tag = next((tag for tag in post.tags if tag.id == tag_id), None)
        if tag is None:
            raise HTTPException(status_code=404,
                                detail="해당 게시글에 연결된 태그를 찾을 수 없습니다.")
        post.tags.remove(tag)
```

- `next(제너레이터, None)`: 조건에 맞는 첫 항목, 없으면 `None`
- `remove()` → 연결 객체가 고아가 되어 `delete-orphan`으로 **그 연결 행만 삭제**. 게시글·태그·다른 게시글의 연결은 유지

### 삭제 범위 정리

| 작업 | `post_mn` | `post_tag_mn` | `tag_mn` |
|------|-----------|---------------|----------|
| 연결 해제 | 유지 | 해당 행만 삭제 | 유지 |
| 게시글 삭제 | 삭제 | 그 게시글의 행 모두 삭제 | **유지** |

## 앱 등록

```python
# main.py
from mysite_many_to_many import models as many_to_many_models     # create_all 전에 import
from mysite_many_to_many.routers.post_router import router as many_to_many_post_router
from mysite_many_to_many.routers.tag_router import router as many_to_many_tag_router

app.include_router(many_to_many_post_router)
app.include_router(many_to_many_tag_router)
```

---

## 동작 확인

`/docs`의 `mysite_many_to_many` 그룹에서 확인합니다.

| 요청 상황 | 처리 |
|-----------|------|
| 같은 이름으로 태그 단독 등록 | 400 |
| 없는 이름의 태그를 게시글에 연결 | 태그 생성 후 연결 |
| 이미 연결된 태그를 다시 연결 | 400 |
| 없는 게시글에 연결·연결 해제 | 404 |
| 없거나 게시글에 연결되지 않은 태그의 연결 해제 | 404 |
| 태그 이름을 중복 입력 | 한 번만 연결 |
| 태그 목록 생략·빈 목록 | 태그 없이 등록 |

태그 이름은 문자열 그대로 비교하므로 `Python`과 `python`은 **다른 태그**입니다.

1. `POST /posts-mn/with-tags`에 `"tags": ["Python", "FastAPI", "Python"]` → `Python`은 한 번만 연결
2. 다른 게시글을 `"tags": ["Python", "SQLAlchemy"]`로 등록 → 두 응답의 `Python` id가 같고, `GET /tags-mn`에도 `Python`은 하나
3. `POST /posts-mn/{post_id}/tags`에 `{"name": "Database"}` → 연결. 같은 요청 반복 → 400. `POST /tags-mn`에 기존 이름 → 400
4. 첫 게시글에서 `Python` 연결 해제 → 첫 게시글엔 없고 두 번째엔 남음. 같은 해제 반복 → 404
5. 첫 게시글 삭제 → 태그 목록과 두 번째 게시글의 연결은 유지

```sql
SELECT * FROM post_tag_mn WHERE post_id = 1;   -- 삭제한 게시글의 연결 행: 없음
SELECT * FROM tag_mn ORDER BY id;              -- 태그 행: 남아 있음
```
