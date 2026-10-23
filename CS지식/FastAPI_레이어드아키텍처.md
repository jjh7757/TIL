# FastAPI 레이어드 아키텍처 — 관심사 분리

앞선 [FastAPI 요청과 응답](FastAPI_요청과응답.md)의 `create_post` 한 함수는 **요청 처리, 입력 검증, 객체 생성, 저장**을 모두 수행했습니다. 기능이 늘수록 이런 함수는 고치기 어려워집니다.

## 관심사 분리 (Separation of Concerns, SoC)

프로그램을 **각각 독립된 관심사로 분리**해, 각 부분이 **단일한 목적**을 갖도록 하는 설계 원칙입니다.

```python
@router.post("", response_model=PostDetailResponse, status_code=201)   # ← 요청 경로·응답 형식
def create_post(post_data: PostCreate):
    global post_id

    if post_data.title == "": raise ...      # ← 입력 검증
    if post_data.content == "": raise ...

    post_id += 1                              # ← ID 부여, 객체 생성
    new_post = Post(post_id, post_data.title, post_data.content)
    posts.append(new_post)                    # ← 저장
    return new_post
```

한 함수에 네 가지 관심사가 섞여 있습니다.

## 레이어드 아키텍처 (Layered Architecture)

FastAPI는 특정 구조를 **강제하지 않는** 자유로운 프레임워크입니다. 레이어드 아키텍처는 관심사 분리를 적용하는 한 방법으로, 코드를 **역할별 계층**으로 나눕니다.

| 계층 | 이 실습 | 담당 |
|------|---------|------|
| Presentation (표현) | **Router** (`APIRouter` 함수) | HTTP 요청·응답. URL, 메서드, 응답 모델, 성공 상태 코드 지정. Pydantic으로 검증된 데이터를 Service에 전달 |
| Business (비즈니스) | **PostService** | 애플리케이션 규칙 확인, 작업 처리 흐름. Repository에 데이터를 요청하고 결과에 따라 계속/중단 |
| Data Access (데이터 접근) | **PostRepository** | 저장소에서 데이터 저장·조회·수정·삭제. 리스트와 ID 카운터 관리. DB를 쓰면 여기서 SQL/ORM 처리 |

### 호출과 반환의 방향

```
클라이언트 ─HTTP 요청→ Router ─작업 호출→ Service ─저장·조회 요청→ Repository
클라이언트 ←HTTP 응답─ Router ←작업 결과─ Service ←처리 결과─ Repository
```

- **호출**은 `Router → Service → Repository` 한 방향
- 결과는 `return`으로 `Repository → Service → Router` 순서로 되돌아온다. 되돌아오는 화살표는 **반환**일 뿐, Repository가 Service나 Router를 호출한다는 뜻이 아니다

## Service가 담당하는 것: 규칙과 처리 흐름

**비즈니스 로직**은 애플리케이션이 지켜야 할 규칙과 그 규칙을 적용하는 절차입니다.

| 작업 | 규칙 | Service의 흐름 |
|------|------|----------------|
| 게시글 수정 | 게시글이 존재, 요청자가 작성자, 내용이 유효 | 조회 → 존재·권한·내용 확인 → 수정 요청 |
| 상품 주문 | 재고 충분, 쿠폰은 조건 충족 시만 적용 | 상품·쿠폰 조회 → 조건 확인 → 금액 계산 → 주문 저장·재고 반영 |

`get_posts()`처럼 추가 규칙이 없으면 Repository 결과를 **그대로 반환**해도 됩니다.

### Pydantic 검증 vs Service 검증

| 구분 | 확인하는 것 | 예 |
|------|-------------|-----|
| Pydantic | 요청 데이터의 **형식·필드 조건** | 필수 값이 있는가? 제목 길이? 주문 수량이 1 이상 정수? |
| Service | **작업을 진행할 수 있는 조건**·업무 규칙 | 수정할 게시글이 존재? 수정 권한? 재고가 충분? |

- 위치는 규칙의 성격에 따라 정한다. 입력값끼리의 비교는 Pydantic에서도, 할인 조건처럼 업무 규칙으로 관리할 검증은 Service에 둘 수도 있다
- 이 실습: `PostCreate`가 필수 필드·타입을, Service가 **빈 문자열**을 검사 (빈 문자열 조건은 `Field`로 Pydantic에서도 가능)
- **게시글 존재 여부**는 Repository 조회 결과로 판단한다: `find_by_id()`가 `None` → `PostService.get_post()`가 `HTTPException`(404) 발생 → 작업 중단

## 계층 분리의 장점

- **유지보수**: 요청 형식이나 저장 방식을 바꿀 때 수정 범위가 줄어든다
- **테스트**: Router를 거치지 않고 Service·Repository 메서드를 **직접 호출**해 확인할 수 있다
- **협업**: 각 계층의 역할과 메서드를 기준으로 작업을 나눌 수 있다

| 변경 사항 | 주로 고칠 계층 |
|-----------|----------------|
| API 경로·성공 상태 코드 변경 | Router |
| 할인 조건·계산 방식 변경 | Service |
| 리스트 저장 → 데이터베이스 저장 | Repository |

저장 방식을 바꿔도 Repository의 **메서드 이름·매개변수·반환 형태를 유지**하면 호출하는 다른 계층의 변경을 줄일 수 있습니다.

---

## 구성: mysite4

```
mysite4/
├── repositories/
│   └── post_repository.py
├── routers/
│   └── post_router.py
├── schemas/
│   └── post.py
└── services/
    └── post_service.py
```

| 파일 | 역할 |
|------|------|
| `schemas/post.py` | 게시글 객체 + 요청·응답 모델 |
| `routers/post_router.py` | HTTP 요청 처리 (`prefix="/posts-layered"`, `tags=["mysite4"]`) |
| `services/post_service.py` | 검증과 작업 흐름. `PostService` 클래스 + `post_service` 객체 |
| `repositories/post_repository.py` | 저장소 CRUD. `PostRepository` 클래스 + `post_repository` 객체 |

`main.py`에서는 `app.include_router(layered_router)`로 라우터를 연결합니다. 각 클래스 정의 아래에서 **객체를 하나 생성해** 다른 계층이 import해 씁니다 (`post_service = PostService()`).

### schemas/post.py

```python
class Post:                          # 저장소가 관리하는 게시글
    def __init__(self, title, content):
        self.id = None               # id는 Repository가 저장할 때 부여
        self.title = title
        self.content = content

class PostCreate(BaseModel):         # 요청 DTO
    title: str
    content: str

class PostDetailResponse(BaseModel): # 응답 DTO (상세)
    id: int
    title: str
    content: str

class PostListResponse(BaseModel):   # 응답 DTO (목록)
    id: int
    title: str
```

이전과 달리 `Post`의 생성자에는 **제목과 내용만** 전달합니다. Service가 만들 때는 아직 id가 없으므로 `id=None`으로 시작합니다.

### Repository — 저장소 관리

```python
class PostRepository:
    def __init__(self):
        self.posts = []
        self.post_id = 0

    def save(self, new_post: Post):
        self.post_id += 1
        new_post.id = self.post_id        # id 부여는 저장소의 일
        self.posts.append(new_post)
        return new_post

    def find_all(self):
        return self.posts

    def find_by_id(self, id: int):
        for post in self.posts:
            if post.id == id:
                return post
        return None                       # 없으면 None — 예외는 Service가 판단

    def update(self, id: int, data: PostCreate):
        for post in self.posts:
            if post.id == id:
                post.title = data.title
                post.content = data.content
                return post
        return None

    def delete(self, id: int):
        for index, post in enumerate(self.posts):
            if post.id == id:
                return self.posts.pop(index)

post_repository = PostRepository()
```

- 리스트와 ID 카운터를 **객체 속성**으로 보관하고 여러 요청이 공유한다 (전역 변수 `global` 불필요)
- Repository는 HTTP를 모른다 → `HTTPException`을 던지지 않고 `None`을 반환
- 서버를 재시작하면 메모리 데이터는 초기화된다

### Service — 검증과 흐름

```python
class PostService:
    def create_post(self, data: PostCreate):
        if data.title == "":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                                detail="title을 입력하세요")
        if data.content == "":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                                detail="content를 입력하세요")

        new_post = Post(title=data.title, content=data.content)
        return post_repository.save(new_post)

    def get_posts(self):
        return post_repository.find_all()       # 추가 규칙 없음 → 그대로 반환

    def get_post(self, id: int):
        post = post_repository.find_by_id(id)
        if post is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="게시글을 찾을 수 없습니다.")
        return post

    def update_post(self, id: int, data: PostCreate):
        (title/content 빈 문자열 검사 → 422)
        self.get_post(id)                        # 존재 확인 (없으면 404)
        return post_repository.update(id, data)

    def delete_post(self, id: int):
        self.get_post(id)                        # 존재 확인 (없으면 404)
        post_repository.delete(id)
```

`get_post()`를 수정·삭제에서도 재사용해 **존재 확인 로직을 한 곳**에 둡니다.

### Router — HTTP만 담당

```python
router = APIRouter(prefix="/posts-layered", tags=["mysite4"])

@router.post("", response_model=PostDetailResponse, status_code=status.HTTP_201_CREATED)
def create_post(data: PostCreate):
    return post_service.create_post(data)

@router.get("", response_model=list[PostListResponse])
def get_posts():
    return post_service.get_posts()

@router.get("/{id}", response_model=PostDetailResponse)
def get_post(id: int):
    return post_service.get_post(id)

@router.put("/{id}", response_model=PostDetailResponse)
def update_post(id: int, data: PostCreate):
    return post_service.update_post(id, data)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(id: int):
    post_service.delete_post(id)
```

Router 함수는 **한 줄**입니다: 경로·메서드·응답 모델·상태 코드를 선언하고 Service를 호출할 뿐, 규칙은 모릅니다.

### 계층별 책임 정리 (CRUD)

| 작업 | Router | Service | Repository |
|------|--------|---------|------------|
| 생성 | POST, 201 | 빈 문자열 검증 → `Post` 생성 | id 부여 + 리스트에 저장 |
| 전체 조회 | GET, 목록 모델 | 그대로 반환 | `find_all` |
| 단일 조회 | GET `/{id}` | `None`이면 404 | `find_by_id` (없으면 `None`) |
| 수정 | PUT `/{id}` | 빈 문자열 → 422, 존재 확인 → 404 | `update` |
| 삭제 | DELETE, 204 | 존재 확인 → 404 | `delete` |

## 실행 확인

```bash
uv run fastapi dev main.py
```

`/docs`의 `mysite4` 그룹에서 확인합니다.

| 요청 | 상태 | 확인 |
|------|------|------|
| 정상 입력으로 생성 | 201 | id, title, content |
| 전체 조회 | 200 | id, title만 |
| 단일 조회·정상 수정 | 200 | id, title, content |
| 빈 제목·내용으로 생성·수정 | 422 | 검증 메시지, **데이터 변경 없음** |
| 없는 ID 조회·삭제, 없는 ID 수정(정상 입력) | 404 | 게시글을 찾을 수 없습니다 |
| 삭제 성공 | 204 | 본문 없음 |

> 수정에서 **검증이 존재 확인보다 먼저**라서, 없는 ID라도 빈 문자열을 보내면 404가 아니라 422가 나온다. 404는 입력이 정상일 때 나온다.
