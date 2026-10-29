# SQLAlchemy 세션과 ORM 객체 상태

ORM 객체는 **세션이 관리하고 있는지**에 따라 동작이 달라집니다. `expire_on_commit=False`로 설정한 **동기** `Session` 기준 설명이며, 게시글(`Post`)·댓글(`Comment`) 모델은 mysite 기준입니다. 각 코드 블록은 독립된 상황입니다.

## 다섯 가지 상태

| 상태 | 뜻 |
|------|----|
| 비영속 transient | 생성했지만 아직 세션에 등록하지 않은 새 객체 |
| 대기 pending | 세션에 등록했지만 아직 INSERT가 실행되지 않은 객체 |
| 영속 persistent | DB에서 조회했거나 INSERT를 실행해 **세션이 관리하는** 객체 |
| 삭제 deleted | DELETE가 실행되었지만 아직 commit되지 않은 객체 |
| 분리(준영속) detached | DB 식별 정보(id)는 있지만 세션에서 분리되어 관리받지 않는 객체 |

```
          add()          flush(INSERT)          delete() + flush(DELETE)
비영속 ─────────▶ 대기 ──────────────▶ 영속 ─────────────────────────▶ 삭제
                                   ▲    │                                │ commit
               get()/select (조회) ┘    │ 세션 종료                      ▼
                                        ▼                               분리
                                       분리
```

> 영속 상태라도 **commit 전에는 저장이 확정된 것이 아니다**. 롤백되면 사라진다.

## 상황별 상태 변화

### 새 게시글을 `add()`

```python
with SessionLocal() as db:
    with db.begin():
        post = Post(title="첫 번째 글")  # 비영속
        db.add(post)                     # 대기: 등록만, INSERT 아직
        db.flush()                       # INSERT 실행 → 영속
    # commit: 저장 확정, post는 영속 유지
# 세션 종료: post는 분리
```

`add()`는 **등록만** 하고 INSERT는 **flush** 때 실행됩니다. `flush()`를 직접 안 불러도 `begin` 블록이 정상 종료되면 flush와 commit이 자동으로 진행됩니다.

### 조회한 게시글의 제목 변경

```python
with SessionLocal() as db:
    with db.begin():
        post = db.get(Post, post_id)  # SELECT → 영속
        post.title = "수정된 제목"     # 영속 유지, 변경 추적
        db.flush()                    # UPDATE 실행
    # commit: 수정 확정
# 세션 종료: 분리
```

영속 객체는 세션이 변경을 감지하므로 다시 `add()`할 필요가 없습니다. UPDATE는 속성을 바꾸는 순간이 아니라 **flush 때** 실행됩니다.

### `post.comments`에 새 댓글 `append()`

```python
with SessionLocal() as db:
    with db.begin():
        post = db.get(Post, post_id)            # post 영속, comments 미조회
        comment = Comment(content="좋은 글입니다")  # comment 비영속
        post.comments.append(comment)           # 댓글 목록 SELECT 후 추가 → comment 대기
        db.flush()                              # 댓글 INSERT → comment 영속
```

- 미조회 상태의 `post.comments`에 접근하면 **그 순간 댓글 목록을 조회**한다
- 관계의 기본 **save-update cascade**가 새 댓글도 세션에 등록하므로 `db.add(comment)` 불필요
- 댓글의 `post_id`는 flush 때 관계에 맞게 채워진다

### 댓글 `delete()`

```python
with SessionLocal() as db:
    with db.begin():
        comment = db.get(Comment, comment_id)  # 영속
        db.delete(comment)                     # 삭제 예약, 아직 영속
        db.flush()                             # DELETE 실행 → 삭제
    # commit: 삭제 확정 → comment는 분리
```

`delete()` 호출과 DELETE 실행 시점은 다릅니다. 삭제가 확정되어도 **파이썬 객체는 남아 있지만** DB 행은 없습니다.

## DTO 변환과 세션

`PostDTO`는 게시글 정보와 댓글 목록을 담고, `from_attributes=True`가 설정되어 있다고 가정합니다.

### ① 게시글만 조회 → begin 밖에서 DTO 변환

```python
with SessionLocal() as db:
    with db.begin():
        post = db.get(Post, post_id)       # comments 미조회
    # commit 후에도 세션은 열려 있음

    dto = PostDTO.model_validate(post)     # comments 접근 → 새 트랜잭션에서 지연 로딩
```

`begin` 블록이 끝나도 **세션은 열려 있으므로** 지연 로딩이 동작합니다.

### ② 댓글까지 미리 조회 → begin 밖에서 DTO 변환

```python
with SessionLocal() as db:
    with db.begin():
        post = db.scalar(
            select(Post).where(Post.id == post_id)
            .options(selectinload(Post.comments))
        )                                  # 게시글 + 댓글 SELECT → 모두 영속

    dto = PostDTO.model_validate(post)     # 이미 읽은 값 사용, 추가 SELECT 없음
```

### ③ 세션까지 닫은 뒤 DTO 변환

```python
with SessionLocal() as db:
    post = db.get(Post, post_id)           # comments 미조회
# 세션 종료: post는 분리

dto = PostDTO.model_validate(post)         # ValidationError
```

`title`은 이미 읽은 값이라 쓸 수 있지만 `comments`를 조회할 **세션이 없습니다**. 관계 접근에서 난 `DetachedInstanceError`가 Pydantic `ValidationError`에 감싸져 나옵니다.

| 경우 | 세션 | comments | 결과 |
|------|------|----------|------|
| ① | 열림 | 미조회 | 지연 로딩으로 성공 (추가 SELECT) |
| ② | 열림 | 미리 로딩 | 성공 (추가 SELECT 없음) |
| ③ | 닫힘 | 미조회 | 실패 |

## `expire_on_commit`의 의미

- 기본값 `True`: commit 후 객체의 속성을 **만료** → 다음 접근 때 DB에서 다시 읽음 (세션이 닫혔으면 실패)
- `False`: commit 후에도 **이미 읽은 값 유지** → 위 예제들처럼 commit 뒤에도 값을 쓸 수 있음

비동기 세션에서 `False`를 쓰는 이유는 [비동기 설정과 Alembic](FastAPI_비동기설정_Alembic.md)에 정리했습니다.

---

상태 이름을 외우기보다 **"지금 세션이 이 객체를 관리하고 있나?"** 를 생각하며 코드를 읽으면 됩니다.
