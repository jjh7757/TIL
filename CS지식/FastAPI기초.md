# FastAPI 기초

FastAPI는 Python 기반 웹 API 프레임워크로, Python 프레임워크 중 최상위권의 속도를 가집니다. 웹 서비스에 필요한 기능을 미리 구현해 두어 **비즈니스 로직에만 집중**할 수 있고, 비동기 처리와 스트리밍 응답을 지원해서 LLM·에이전트 기능을 HTTP API로 제공하는 데 쓰기 좋습니다.

## 클라이언트와 서버의 요청·응답

```
클라이언트(브라우저·앱) ──HTTP 요청──▶ 서버(FastAPI 애플리케이션)
                       ◀─HTTP 응답(JSON 등)──
```

- **클라이언트**: 서버에 기능이나 데이터를 요청하는 쪽 (브라우저, 앱)
- **서버**: 요청을 처리하고 결과를 응답으로 돌려주는 쪽 — FastAPI는 이 서버 쪽 애플리케이션을 만든다

## 프로젝트 준비

```bash
uv init fastapi_basic
cd fastapi_basic
uv add "fastapi[standard]"
```

- `fastapi[standard]`는 FastAPI와 함께 **개발 서버 실행에 필요한 도구**까지 설치한다
- 이 과정에서 가상환경 `.venv`가 만들어지고 패키지가 설치된다

## 첫 API

```python
# main.py
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}
```

| 코드 | 의미 |
|------|------|
| `app = FastAPI()` | 요청을 처리할 애플리케이션 객체 생성 |
| `@app.get("/")` | 루트 경로 `/`로 들어오는 **GET 요청을 아래 함수와 연결**하는 데코레이터 |
| `def read_root()` | 해당 요청을 받으면 실행되는 함수 |
| `return {...}` | 딕셔너리를 반환하면 FastAPI가 **JSON 응답으로 자동 변환** |

## 개발 서버 실행

```bash
uv run fastapi dev main.py
```

- 코드를 저장하면 서버가 **자동으로 다시 로드**된다
- `Ctrl + C`로 종료
- 실행 중 `http://127.0.0.1:8000/`에 접속하면 `{"Hello": "World"}` 확인

## 엔드포인트와 응답

**엔드포인트**는 클라이언트가 특정 기능을 요청하는 API의 접점으로, **HTTP 메서드 + URL 경로**로 구분합니다. 위 코드의 엔드포인트는 `GET /`입니다. 하나의 앱에 여러 개를 둘 수 있습니다.

```python
@app.get("/hello")
def hello():
    return "Hello World!"        # 응답 본문: "Hello World!"  (JSON 문자열)


@app.get("/hi")
def hi():
    return ["hello", "World", "!"]   # 응답 본문: ["hello", "World", "!"]  (JSON 배열)
```

| 반환값 | JSON 응답 |
|--------|-----------|
| `dict` | 객체 `{...}` |
| `list` | 배열 `[...]` |
| `str` | 문자열 `"..."` (따옴표 포함) |

## 자동 문서화

FastAPI는 등록된 엔드포인트로 **API 명세서를 자동 생성**합니다.

| 주소 | 도구 | 용도 |
|------|------|------|
| `http://127.0.0.1:8000/docs` | Swagger UI | 명세 확인 + **요청 직접 실행** |
| `http://127.0.0.1:8000/redoc` | ReDoc | 명세 확인 |

Swagger UI에서 엔드포인트를 펼쳐 **Try it out → Execute**를 누르면 상태 코드(200)와 응답 본문을 바로 확인할 수 있습니다.

---

# 간단한 게시판 (CRUD)

게시글은 `id`, `제목`, `내용`으로 구성되고, API로 **생성·조회·수정·삭제(CRUD)** 합니다.

## RESTful API 설계

자원을 **URL**로, 자원에 대한 행위를 **HTTP 메서드**로 구분합니다. 게시글 목록은 `/posts`, 특정 게시글은 `/posts/{id}`.

| 기능 | 메서드 | 경로 | 데코레이터 |
|------|--------|------|------------|
| 게시글 생성 | POST | `/posts` | `@router.post("")` |
| 전체 조회 | GET | `/posts` | `@router.get("")` |
| 단일 조회 | GET | `/posts/{id}` | `@router.get("/{id}")` |
| 수정 | PUT | `/posts/{id}` | `@router.put("/{id}")` |
| 삭제 | DELETE | `/posts/{id}` | `@router.delete("/{id}")` |

- **PUT**은 자원 **전체** 수정, **PATCH**는 **일부** 수정. 이 예제는 제목·내용을 모두 바꾸므로 PUT 사용

## 파일 구조

| 파일 | 역할 |
|------|------|
| `main.py` | FastAPI 앱 생성 + 게시판 라우터 연결 |
| `mysite/post.py` | 게시글 데이터 구조 정의 |
| `mysite/post_api.py` | 게시글 저장 + CRUD 요청 처리 |

### 게시글 클래스

```python
# mysite/post.py
class Post:

    def __init__(self, id, title, content):
        self.id = id
        self.title = title
        self.content = content
```

### 라우터와 저장소

```python
# mysite/post_api.py
from fastapi import APIRouter
from .post import Post

router = APIRouter(prefix="/posts", tags=["mysite"])

# 게시글 객체들을 저장하는 리스트와 초기 데이터
posts = [Post(1, "기본 제목", "기본 내용")]
post_id = 1
```

- `posts`: 게시글 객체 리스트 (저장소 역할)
- `post_id`: 마지막으로 부여한 식별 번호
- `APIRouter`: **main.py와 별도 파일**에 정의한 엔드포인트를 묶는 단위
- `prefix="/posts"`: 각 엔드포인트 경로 앞에 붙는 공통 경로
- `tags=["mysite"]`: Swagger UI에서 `mysite` 그룹으로 묶어 표시

> 게시글이 **메모리**에 저장되므로 서버가 재시작되거나 코드 변경으로 reload되면 **초기 데이터로 돌아간다**.

### 라우터 연결

```python
# main.py
from fastapi import FastAPI
from mysite.post_api import router as post_router

app = FastAPI()

app.include_router(post_router)   # 라우터를 앱에 등록
```

## CRUD 구현

### Create — 게시글 작성

```python
@router.post("")
def create_post():
    global post_id
    post_id += 1                      # 식별자 1 증가

    post = Post(post_id, "제목", "내용")
    posts.append(post)

    return post
```

- 함수 안에서 모듈 변수 `post_id`를 바꾸려면 `global` 선언이 필요하다

### Read — 전체 조회

```python
@router.get("")
def get_posts():
    return posts
```

### 경로 매개변수 (path parameter)

- 주소 경로에 **변수를 포함해 데이터를 전달**하는 방식. 중괄호로 변수명 지정
- `/posts/{id}`에서 `/posts/1`로 요청하면 함수의 `id` 매개변수에 `1`이 전달된다
- 함수 매개변수를 `id: int`로 선언하면 FastAPI가 **정수로 변환하고 검증**한다

### Read — 단일 조회

```python
@router.get("/{id}")
def get_post(id: int):
    for post in posts:
        if post.id == id:
            return post
    return None
```

### Update — 수정

```python
@router.put("/{id}")
def update_post(id: int):
    for post in posts:
        if post.id == id:
            post.title = "수정된 제목"
            post.content = "수정된 내용"
            return post
    return None
```

### Delete — 삭제

```python
@router.delete("/{id}")
def delete_post(id: int):
    for i, post in enumerate(posts):
        if post.id == id:
            return posts.pop(i)      # 리스트에서 제거하고 그 게시글을 반환

    return "삭제 실패"
```

- `enumerate`로 인덱스(`i`)와 객체(`post`)를 함께 꺼내 `pop(i)`로 제거

## 실행 확인

서버를 재시작해 초기 데이터로 돌린 뒤 `/docs`(Swagger UI)에서 순서대로 실행하고, **응답을 먼저 예상한 뒤 실제 결과와 비교**한다.

| 요청 | 확인할 내용 |
|------|-------------|
| `GET /posts` | 초기 게시글(id=1) 조회 |
| `POST /posts` | 제목 "제목", 내용 "내용"인 게시글(id=2) 생성 |
| `GET /posts/2` | 생성한 게시글 조회 |
| `PUT /posts/2` | 제목·내용이 "수정된 제목"·"수정된 내용"으로 변경 |
| `GET /posts/2` | 변경된 내용 조회 |
| `DELETE /posts/2` | 삭제 + 삭제한 게시글이 응답으로 반환 |
| `GET /posts` | 삭제한 게시글이 목록에 없음 |

- 브라우저 주소창으로 접속하면 **GET 요청**만 보낸다. 생성·수정·삭제는 Swagger UI에서 해당 메서드 항목을 골라 실행한다

## 이 예제의 한계 (다음에 개선할 점)

- 생성·수정이 **고정 문자열**("제목", "수정된 제목")만 쓴다 — 클라이언트가 보낸 값(요청 바디)을 받지 않는다
- 없는 id를 조회·수정하면 `None`(JSON `null`)이 **200으로 응답**된다 — 404 같은 적절한 상태 코드가 아니다 ([HTTP 상태 코드](HTTP상태코드.md) 참고)
- 삭제 실패는 문자열 `"삭제 실패"`를 반환할 뿐 에러로 처리하지 않는다
- 메모리 저장이라 재시작하면 데이터가 사라진다 — 영속화하려면 DB 필요 ([데이터베이스 기초](데이터베이스기초.md))
