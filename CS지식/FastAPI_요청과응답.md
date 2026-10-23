# FastAPI 요청과 응답 — Pydantic, 쿼리 파라미터, 응답 모델, Validation

[FastAPI 기초](FastAPI기초.md)의 게시판은 고정 문자열만 저장했습니다. 여기서는 **클라이언트가 보낸 값을 받아 검증**하고, **상태 코드와 응답 모델로 결과를 전달**하도록 발전시킵니다.

## Pydantic과 요청 본문(Request Body)

**Pydantic**은 파이썬 타입 힌트로 데이터 구조를 정의하고 입력값을 검증하는 라이브러리입니다. FastAPI에서는 클라이언트가 보내는 요청 데이터의 형식을 정의하는 데 씁니다.

- `BaseModel`을 상속하고 필드 이름과 타입을 선언한다
- **기본값이 없는 필드는 필수**, 기본값이 있으면 생략 가능
- 입력값은 모델 규칙에 따라 타입 변환·검증을 거친다. 필수 필드 누락·허용되지 않는 값이면 검증 실패

**요청 본문**은 클라이언트가 서버에 보낼 데이터를 담는 영역입니다. 생성·수정 시 제목과 내용을 JSON으로 담아 보내고, FastAPI가 Pydantic 모델로 받아 검증합니다.

```python
# mysite2/post.py
from pydantic import BaseModel


class PostCreate(BaseModel):      # 요청 데이터 형식
    title: str
    content: str


class Post:                       # 서버가 관리하는 게시글
    def __init__(self, id, title, content):
        self.id = id
        self.title = title
        self.content = content
```

> `str` 선언만으로는 **길이를 제한하지 않는다** — 빈 문자열 `""`도 통과한다.

### 요청 DTO vs 게시글 객체

DTO(Data Transfer Object)는 데이터를 주고받을 때 값을 묶어 담는 객체입니다.

| 클래스 | 데이터 | 역할 |
|--------|--------|------|
| `PostCreate` | title, content | 클라이언트가 보낸 요청 데이터. Pydantic이 필수 값·타입 검증 |
| `Post` | id, title, content | 서버가 관리하는 게시글. `posts` 리스트에 저장 |

요청으로 받는 데이터(id 없음)와 서버가 관리하는 데이터(id 있음)의 구성이 다르므로 **두 클래스로 구분**합니다. id는 서버가 부여합니다.

### 요청 본문 받기

매개변수를 `post_data: PostCreate`로 선언하면 FastAPI가 **JSON 본문을 읽고 검증해 객체로 전달**합니다.

```python
# mysite2/post_api.py
router = APIRouter(prefix="/posts-pydantic", tags=["mysite2"])
posts = []
post_id = 0


@router.post("")
def create_post(post_data: PostCreate):
    global post_id
    post_id += 1

    new_post = Post(post_id, post_data.title, post_data.content)
    posts.append(new_post)
    return new_post


@router.put("/{id}")
def update_post(id: int, updated_post: PostCreate):   # 경로(id) + 본문(PostCreate)
    for post in posts:
        if post.id == id:
            post.title = updated_post.title
            post.content = updated_post.content
            return post
    return {"message": "수정할 대상이 없습니다."}
```

처리 흐름: **JSON 요청 본문 → `PostCreate` 검증 → 함수 실행 → JSON 응답**. 검증에 실패하면 **함수가 실행되지 않고** 검증 오류 응답이 나갑니다. 수정(PUT)은 제목·내용을 모두 받으므로 생성과 같은 `PostCreate`를 재사용합니다.

### 검증 결과 확인 (POST 본문별)

| 요청 본문 | 결과 |
|-----------|------|
| `{"title": "제목", "content": "내용"}` | 통과, 생성 |
| `{"title": "제목"}` | `content` 누락 → 실패 |
| `{"title": ["제목"], "content": "내용"}` | `title`이 리스트 → 실패 |
| `{"title": "제목", "content": null}` | `None` 불허 → 실패 |

실패 응답의 `detail`에서 **오류 필드와 이유**를 확인하고, 이후 목록 조회로 잘못된 요청이 저장되지 않았는지 봅니다.

---

## 경로 파라미터 vs 쿼리 파라미터

| 구분 | 위치 | 예 | 용도 |
|------|------|-----|------|
| 경로(Path) | URL 경로 일부 | `/posts-response/1` | 특정 자원 식별 |
| 쿼리(Query) | `?` 뒤 `key=value` | `/search?keyword=FastAPI` | 검색·필터·정렬 조건 |
| 본문(Body) | HTTP 요청 본문 | `{"title": ..., "content": ...}` | 생성·수정할 데이터 |

**FastAPI가 위치를 자동 구분**합니다 (선언 순서와 무관).

- 경로의 `{변수명}`과 이름이 같은 매개변수 → **경로**에서 받음
- 경로에 없는 `int`/`str`/`bool` 같은 단순 타입 → **쿼리 파라미터**
- `PostCreate` 같은 Pydantic 모델 → **요청 본문**
- 타입 힌트(`id: int`)는 값을 **변환·검증**하는 데 쓰인다

### 검색 엔드포인트

```python
@router.get("/search", response_model=list[PostListResponse])
def search_posts(keyword: str | None = None):
    if keyword:
        return [post for post in posts if keyword in post.title]
    return posts
```

- `str | None`은 문자열 또는 None 허용, `= None`은 생략 시 기본값
- `keyword`를 생략하거나 빈 문자열이면 **전체 반환**
- ⚠️ **`/search`를 `/{id}`보다 먼저 정의**해야 한다. FastAPI는 등록 순서대로 경로를 매칭하므로, 순서가 반대면 `search`가 `id`로 해석된다

`Query()`로 쿼리 파라미터임을 명시할 수도 있습니다. 클라이언트 요청은 동일합니다.

```python
from fastapi import Query

def search_posts(keyword: str | None = Query(default=None)): ...
```

`Query()`는 받을 위치와 설정(검증 조건·설명 등)을 선언하는 도구이고, 같은 방식으로 경로는 `Path()`, 본문은 `Body()`로 명시할 수 있습니다.

---

## HTTP 상태 코드와 예외 처리

| 코드 | 의미 | 게시판에서의 용도 |
|------|------|------------------|
| 200 | 성공 | 조회·수정 성공 (기본값) |
| 201 | 자원 생성 성공 | 게시글 생성 |
| 204 | 성공, **응답 본문 없음** | 게시글 삭제 |
| 404 | 자원 없음 | 요청한 게시글이 없음 |
| 422 | 요청 데이터 검증 실패 | 필수 필드 누락, 허용 안 되는 타입 |

(코드 전체 의미는 [HTTP 상태 코드](HTTP상태코드.md) 참고.) `PostCreate` 규칙에 맞지 않으면 FastAPI가 **자동으로 422**를 반환합니다.

### HTTPException

`{"message": "찾을 수 없습니다"}`를 `return`하면 **상태 코드는 여전히 200**입니다. 오류 상태 코드를 보내려면 `HTTPException`을 `raise`합니다.

```python
from fastapi import APIRouter, HTTPException, status

raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
```

- `raise`하면 **해당 요청 처리가 중단**되고, FastAPI가 404와 `{"detail": "게시글을 찾을 수 없습니다."}`를 보낸다
- 별도의 `try-except` 불필요
- `status` 모듈은 `status.HTTP_201_CREATED` 같은 **상태 코드 상수**를 제공한다

### 생성·삭제의 상태 코드 지정

```python
@router.post("", response_model=PostDetailResponse,
             status_code=status.HTTP_201_CREATED)
def create_post(post_data: PostCreate): ...


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(id: int):
    for index, post in enumerate(posts):
        if post.id == id:
            posts.pop(index)
            return                      # 204는 본문이 없으므로 아무것도 반환하지 않음
    raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
```

---

## 응답 모델(response_model)

**응답 DTO**는 서버가 클라이언트에 보낼 데이터의 구조를 정의합니다. 요청 모델이 입력 형식을 정하듯, 응답 모델은 **반환 필드와 타입**을 정합니다.

```python
class PostListResponse(BaseModel):     # 목록·검색: 가볍게
    id: int
    title: str


class PostDetailResponse(BaseModel):   # 상세·생성·수정: content까지
    id: int
    title: str
    content: str
```

| 함수 | 데코레이터 |
|------|------------|
| `get_posts` | `@router.get("", response_model=list[PostListResponse])` |
| `search_posts` | `@router.get("/search", response_model=list[PostListResponse])` |
| `get_post` | `@router.get("/{id}", response_model=PostDetailResponse)` |
| `create_post` | `@router.post("", response_model=PostDetailResponse, status_code=201)` |
| `update_post` | `@router.put("/{id}", response_model=PostDetailResponse)` |

- FastAPI는 반환 데이터를 응답 모델에 맞게 **검증하고, 모델에 정의된 필드만 포함**한다. `Post` 객체에 `content`가 있어도 `PostListResponse`로 나가는 응답에서는 **제외**된다 (불필요한 정보 노출 방지)
- 응답 모델은 **정상 응답**의 형식. 게시글이 없을 때는 `HTTPException`으로 오류 응답을 보낸다
- 메시지 딕셔너리를 정상 응답으로 `return`하면 필수 필드가 없어 **응답 검증 오류**가 난다 → 앞서 `return {"message": ...}` 방식이 `response_model`과 함께 쓸 수 없는 이유

### 응답 확인

| 요청 | 상태 | 확인 |
|------|------|------|
| `POST /posts-response` | 201 | id, title, content |
| `GET /posts-response` | 200 | id, title만 |
| `GET /posts-response/search?keyword=FastAPI` | 200 | 제목에 포함된 글의 id, title |
| `GET /posts-response/{id}` | 200 | id, title, content |
| `PUT /posts-response/{id}` | 200 | 변경된 id, title, content |
| `DELETE /posts-response/{id}` | 204 | 본문 없음 |
| 삭제한 id로 조회·수정·삭제 | 404 | detail 메시지 |
| content 없이 생성 | 422 | 필수 필드 누락 오류 |

---

## 간단한 Validation

**Validation(유효성 검증)**은 입력 데이터가 정한 조건에 맞는지 **저장·수정 전에** 검사해 잘못된 데이터가 들어가는 것을 막는 과정입니다.

| 검증 기준 | 확인 내용 | 담당 |
|-----------|-----------|------|
| 필수 여부 | 제목·내용이 요청에 있는가 | Pydantic (자동) |
| 타입 | 문자열인가 | Pydantic (자동) |
| 값의 조건 | 빈 문자열은 아닌가 | **직접 추가 필요** |

`{"title": "", "content": "내용"}`은 title이 있고 문자열이므로 Pydantic을 통과합니다. **타입이 맞아도 값이 조건을 만족하는지는 별도로 확인**해야 합니다.

```python
def create_post(post_data: PostCreate):
    global post_id

    if post_data.title == "":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="title을 입력하세요",
        )
    if post_data.content == "":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="content를 입력하세요",
        )

    post_id += 1                      # 검증 통과 후에만 id 증가·저장
    new_post = Post(post_id, post_data.title, post_data.content)
    posts.append(new_post)
    return new_post
```

- 검증을 **저장 코드보다 앞**에 둔다 → 실패하면 예외로 중단되어 id가 늘거나 저장되지 않는다
- `update_post`도 같은 검사를 먼저 하고, 통과한 뒤에 대상 게시글을 찾는다 (없으면 404)
- 결과: 빈 값 → **422**, 정상 생성 → **201**, 정상 수정 → **200**
- 이 정도의 단순 조건은 Pydantic의 **`Field`**(예: 최소 길이)로도 설정할 수 있다 — 이 실습에서는 `if`로 직접 검사했다
- 위 `if` 검사가 생성·수정 함수에 **중복**되어 있다는 점이 다음 문서([FastAPI 레이어드 아키텍처](FastAPI_레이어드아키텍처.md))의 출발점이 된다
