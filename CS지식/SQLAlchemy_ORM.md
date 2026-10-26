# SQLAlchemy ORM 기초

[FastAPI DB 연동](FastAPI_DB연동.md) 게시판에서 사용한 SQLAlchemy의 주요 메서드를 정리합니다. 예제의 `Post`는 게시글 모델, `db`는 세션입니다. 수정·삭제 예제는 대상 게시글이 존재한다고 가정합니다.

## ORM (Object-Relational Mapping)

파이썬 **클래스·객체**를 DB **테이블·행**과 연결하는 기술입니다. SQL 대신 클래스와 메서드로 데이터를 생성·조회·수정·삭제합니다.

- **생산성**: 반복적인 SQL 작성을 줄인다
- **유지보수**: 공통 CRUD 코드를 여러 데이터베이스에서 재사용하기 쉽다
- **직관적**: 데이터를 파이썬 객체와 속성으로 다룬다

## 변경 사항 반영과 트랜잭션

**트랜잭션**은 여러 DB 작업을 하나로 묶어 **확정하거나 취소**하는 단위입니다.

| 메서드 | 역할 |
|--------|------|
| `add()` | 새 객체를 세션에 등록 |
| `flush()` | 변경 사항을 SQL로 실행하되 확정하지 않음 |
| `commit()` | flush한 뒤 트랜잭션 확정 |
| `rollback()` | 아직 확정하지 않은 변경 취소 |
| `refresh()` | DB에서 객체의 값을 다시 조회 |

> 게시판 예제의 Service는 `commit()`을 직접 부르지 않고 `with db.begin():` 블록으로 감싸 정상 종료 시 commit, 예외 시 rollback을 자동으로 처리한다.

## 생성

```python
# 단일 추가
new_post = Post(title="첫 번째 글", content="내용입니다")
db.add(new_post)
db.commit()
```
```sql
INSERT INTO posts (title, content) VALUES ('첫 번째 글', '내용입니다') RETURNING posts.id;
```

`RETURNING posts.id`로 DB가 만든 id를 받아 `new_post.id`에 채워 줍니다.

```python
# 일괄 추가
db.add_all([
    Post(title="두 번째", content="내용2"),
    Post(title="세 번째", content="내용3"),
])
db.commit()
```

## 기본키 조회 — `get()`

```python
post = db.get(Post, 1)      # 없으면 None
```
```sql
SELECT posts.id, posts.title, posts.content FROM posts WHERE posts.id = 1;
```

## 조회문 구성과 실행

조회문(`stmt`, Statement)을 **만든 뒤** 세션으로 **실행**합니다.

| 코드 | 역할 |
|------|------|
| `select(Post)` | 게시글을 조회할 구문 생성 |
| `db.scalars(stmt)` | 실행하고 조회된 **객체들**을 꺼낼 수 있게 함 |
| `db.scalar(stmt)` | 실행하고 **첫 번째 객체** 반환. 없으면 `None` |

`db.scalars(stmt)` 뒤에 붙이는 결과 추출 메서드:

| 메서드 | 결과 있음 | 없음 | 여러 개 |
|--------|-----------|------|---------|
| `.all()` | 리스트 | `[]` | 리스트 |
| `.first()` | 첫 번째 | `None` | 첫 번째 |
| `.one()` | 그 하나 | **오류** | **오류** |
| `.one_or_none()` | 그 하나 | `None` | **오류** |

## 조회 예제

| 목적 | 파이썬 | SQL |
|------|--------|-----|
| 전체 | `select(Post)` | `SELECT ... FROM posts` |
| 단일 조건 | `select(Post).where(Post.id == 1)` | `WHERE posts.id = 1` |
| 키워드 검색 | `select(Post).where(Post.title.like("%FastAPI%"))` | `WHERE posts.title LIKE '%FastAPI%'` |
| AND | `.where(Post.id > 10, Post.title.like("%공부%"))` | `WHERE posts.id > 10 AND posts.title LIKE '%공부%'` |
| OR | `.where(or_(Post.id == 1, Post.title == "공지"))` | `WHERE posts.id = 1 OR posts.title = '공지'` |
| 정렬 | `.order_by(Post.id.desc())` | `ORDER BY posts.id DESC` |
| 개수 제한 | `.order_by(Post.id.desc()).limit(10)` | `ORDER BY posts.id DESC LIMIT 10` |

- `where()`에 조건을 여러 개 넣으면 **AND**로 묶인다
- `or_`, `and_`는 `from sqlalchemy import or_, and_`로 import

```python
# 복합 조건
stmt = select(Post).where(
    and_(
        Post.id > 10,
        or_(Post.title == "공지", Post.title == "이벤트"),
    )
)
posts = db.scalars(stmt).all()
```
```sql
WHERE posts.id > 10 AND (posts.title = '공지' OR posts.title = '이벤트');
```

게시판의 목록 조회 `db.scalars(select(Post).order_by(Post.id)).all()`은 **"전체 + 정렬 + 리스트로"** 의 조합입니다.

## 수정 — 더티 체킹

조회한 객체의 **속성을 바꾸고 commit**하면 저장됩니다. SQLAlchemy가 객체의 변경을 자동으로 감지하는 것을 **더티 체킹**(변경 감지)이라고 합니다.

```python
post = db.get(Post, 1)
post.title = "수정된 제목"
db.commit()                 # flush 시 UPDATE 실행
```

## 삭제

```python
post = db.get(Post, 1)
db.delete(post)
db.commit()
```
```sql
DELETE FROM posts WHERE posts.id = 1;
```

---

페이지네이션(`offset`), 전체 개수 조회(`func.count`), 특정 컬럼 조회 등은 기능을 확장할 때 필요한 문법을 찾아 적용합니다.
