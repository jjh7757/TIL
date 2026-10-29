# FastAPI 공통 응답과 예외 처리

`fastapi_agent`의 회원·게시글·댓글 API에 **성공·실패 응답 형식을 통일**하는 규칙을 적용합니다.

## 공통 응답을 쓰는 이유

성공 데이터는 `data`, 안내 문구는 `message`, 오류 정보는 `error`처럼 **항상 같은 위치**에 담으면:

- 클라이언트가 데이터 추출·오류 처리 코드를 **모든 API에서 재사용**할 수 있다
- 각 Router가 응답 필드를 직접 구성할 필요가 줄어든다
- FastAPI가 모델대로 응답을 검증하고 **API 문서에 표시**하므로 받을 형식이 명확하다

## 응답 규칙

| 상황 | 상태 코드 | 본문 |
|------|-----------|------|
| 조회·수정·로그인 성공 | 200 | `{"data": ..., "message": ...}` |
| 생성 성공 | 201 | `{"data": ..., "message": ...}` |
| 삭제 성공 | **200** | `{"data": null, "message": "삭제 안내 문구"}` |
| 요청 처리 실패 | 4xx, 5xx | `{"error": ...}` |

- 성공 여부는 본문의 `success: true` 같은 필드가 아니라 **HTTP 상태 코드**로 구분한다
- 삭제가 204가 아니라 200인 이유: 204는 **본문을 가질 수 없어** 안내 문구를 담을 수 없다

## 구성 파일

| 파일 | 역할 |
|------|------|
| `core/responses.py` | 성공·오류 응답 모델, API 문서용 오류 예시 |
| `core/exceptions.py` | 오류 종류별 예외 클래스와 공통 부모 `ApiException` |
| `core/exception_handlers.py` | 예외 → 공통 HTTP 오류 응답 변환 |
| `main.py` | 전역 예외 핸들러 등록 |
| 도메인 `router.py` | 성공 응답 모델 선언, 응답 객체 생성 |
| 도메인 `service.py` | 업무 조건에 따라 예외 발생 |

---

## 성공 응답

### 제네릭 성공 모델

```python
# core/responses.py
from pydantic import BaseModel


class SuccessResponse[T](BaseModel):
    data: T
    message: str | None = None
```

- `class SuccessResponse[T]`는 **제네릭 클래스** 선언 문법 (Python 3.12+). `T`는 사용할 때 타입을 받는 **타입 매개변수**
- `SuccessResponse[PostDetailResponse]`이면 `T = PostDetailResponse`가 되고, Pydantic이 `data`를 그 모델로 검증한다
- `message`는 사용자에게 보여줄 안내 문구. 지정하지 않으면 `null`

| 모델 | `data` |
|------|--------|
| `SuccessResponse[UserResponse]` | 회원 한 명 |
| `SuccessResponse[PostDetailResponse]` | 게시글 한 개 |
| `SuccessResponse[list[PostListResponse]]` | 게시글 목록 |
| `SuccessResponse[TokenResponse]` | 토큰과 토큰 타입 |
| `SuccessResponse[None]` | 삭제 완료 시 `null` |

### Router에서 구성

```python
router = APIRouter(prefix="/posts", tags=["posts"], responses=error_responses(422))


@router.post(
    "",
    response_model=SuccessResponse[PostDetailResponse],
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(401),
)
async def create_post(
    data: PostCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    post = await post_service.create_post(db, data, current_user)
    return SuccessResponse[PostDetailResponse](data=post, message="게시글이 등록되었습니다.")


@router.get("", response_model=SuccessResponse[list[PostListResponse]])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    posts = await post_service.get_posts(db)
    return SuccessResponse[list[PostListResponse]](data=posts)
```

- Router는 Service 결과를 `data`에 담고 필요하면 `message`를 지정한다
- `error_responses()`는 `core/responses.py`에 **직접 정의한 문서용 함수**. `responses=error_responses(401)`은 Swagger에 401 오류 모델·예시를 **표시만** 한다. 오류를 발생시키거나 응답을 만들지 않는다
- 인증 정보가 없거나 토큰이 유효하지 않으면 `get_current_user()`가 `UnauthorizedException`을 발생 → 전역 핸들러가 401로 변환

게시글이 없을 때 목록 응답: `{"data": [], "message": null}`

## 오류 응답

### 예외 처리를 공통화하는 이유

업무 오류·입력 검증 오류·서버 오류를 **같은 `error` 구조**로 응답하면, 클라이언트는 `error.code`로 종류를 구분하고 `error.message`를 화면에 띄우는 코드를 재사용할 수 있습니다. 서버에서는 **Service는 예외만 발생**시키고 **전역 핸들러가 응답과 로그**를 맡아, 오류 처리 코드가 한곳에 모입니다.

### 구성 요소

| 구성 요소 | 종류 | 역할 |
|-----------|------|------|
| `ValidationIssue` | Pydantic 모델 | 입력 검증 오류 **한 건**의 위치·설명·종류 (`error.details`의 항목) |
| `ErrorDetail` | Pydantic 모델 | 오류 코드·메시지·검증 오류 목록 (응답의 `error`) |
| `ErrorResponse` | Pydantic 모델 | `{"error": ...}` 전체 본문 |
| `ApiException` | 공통 부모 예외 | 상태 코드·오류 코드·메시지·헤더 보관. 자식 예외를 **하나의 핸들러**로 처리 |
| `NotFoundException` 등 | `ApiException` 자식 | 오류 종류별 상태 코드·기본 메시지 지정 |
| `api_exception_handler()` | 예외 핸들러 | 예외를 받아 오류 모델로 본문을 만들고 상태 코드·헤더를 적용 |

### 오류 모델

```python
# core/responses.py (발췌)
class ValidationIssue(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[ValidationIssue] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorDetail
```

```json
{
  "error": {
    "code": "POST_NOT_FOUND",
    "message": "게시글을 찾을 수 없습니다.",
    "details": []
  }
}
```

`code`는 **프로그램이** 오류를 구분하는 값, `message`는 **사람이** 읽을 설명입니다. 일반 업무 오류의 `details`는 빈 배열입니다.

### 커스텀 예외

| 예외 클래스 | 상태 | 사용 상황 |
|-------------|------|-----------|
| `NotFoundException` | 404 | 조회 대상 없음 |
| `UnauthorizedException` | 401 | 인증 정보 없음·유효하지 않음 |
| `ForbiddenException` | 403 | 작업 권한 없음 |
| `ConflictException` | 409 | 이메일 중복 등 현재 데이터와 충돌 |

```python
# core/exceptions.py
class ApiException(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code   # HTTP 상태 코드
        self.code = code                 # 본문 error.code
        self.message = message           # 본문 error.message
        self.headers = headers           # HTTP 헤더


class NotFoundException(ApiException):
    def __init__(
        self, message: str = "요청한 리소스를 찾을 수 없습니다.", *, code: str = "NOT_FOUND"
    ):
        super().__init__(status_code=404, code=code, message=message)


class UnauthorizedException(ApiException):
    def __init__(self, message: str = "인증이 필요합니다.", *, code: str = "UNAUTHORIZED"):
        super().__init__(
            status_code=401,
            code=code,
            message=message,
            headers={"WWW-Authenticate": "Bearer"},
        )

# ForbiddenException(403, "FORBIDDEN"), ConflictException(409, "CONFLICT")도 같은 형태
```

`*` 뒤의 `code`는 **키워드 전용 인자** → `NotFoundException("메시지", code="POST_NOT_FOUND")`처럼 이름을 붙여야만 전달됩니다.

### Service에서 예외 발생

```python
if post is None:
    raise NotFoundException()                    # 기본 코드·메시지

if post is None:
    raise NotFoundException(
        code="POST_NOT_FOUND",
        message="게시글을 찾을 수 없습니다.",
    )
```

같은 404라도 `POST_NOT_FOUND`, `COMMENT_NOT_FOUND`처럼 `code`로 세부 상황을 구분합니다. `async with db.begin()` 안에서 예외가 나면 **트랜잭션이 롤백**되고 전역 핸들러가 오류 응답을 만듭니다.

이전 실습에서 Service가 `HTTPException`을 직접 던진 것과 비교하면, Service는 **HTTP 응답 형식을 몰라도** 됩니다.

### 전역 예외 핸들러

```python
# core/exception_handlers.py (발췌)
async def api_exception_handler(request: Request, exc: ApiException) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=exc.code, message=exc.message))
    return JSONResponse(
        status_code=exc.status_code,
        content=body.model_dump(mode="json"),
        headers=exc.headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiException, api_exception_handler)
    app.add_exception_handler(HTTPException, http_error_handler)          # starlette의 HTTPException
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
```

- 핸들러는 `JSONResponse`를 **직접** 반환하므로 `response_model`이 적용되지 않는다 → 오류 모델을 만들고 `model_dump(mode="json")`으로 JSON 가능한 값으로 변환
- 부모 `ApiException`에 등록한 핸들러가 **자식 예외 네 가지도 처리**

| 예외 | 처리 |
|------|------|
| `ApiException`과 자식 | 예외에 지정된 상태 코드·코드·메시지·헤더 |
| Starlette `HTTPException` | 등록되지 않은 경로 404, 허용하지 않는 메서드 405 등. FastAPI의 `HTTPException`도 이를 상속하므로 함께 처리 |
| `RequestValidationError` | 입력 검증 오류 → 422 공통 응답 |
| `Exception` | 예상하지 못한 오류 → 로그 기록 + 500 공통 응답 |

```python
# main.py (발췌)
app = FastAPI(title="FastAPI Agent", lifespan=lifespan, responses=error_responses(500))
register_exception_handlers(app)
```

### 입력 검증 오류 (422)

```python
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        ValidationIssue(loc=list(error["loc"]), msg=error["msg"], type=error["type"])
        for error in exc.errors()
    ]
    body = ErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR", message="입력값을 확인해 주세요.", details=details
        )
    )
    return JSONResponse(status_code=422, content=body.model_dump(mode="json"))
```

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "입력값을 확인해 주세요.",
    "details": [
      {"loc": ["body", "title"], "msg": "Field required", "type": "missing"}
    ]
  }
}
```

- `loc`: 오류 위치 (`body`=요청 본문, `path`=경로 매개변수), `msg`: 설명, `type`: 오류 종류
- `exc.errors()`의 각 항목에는 원본 입력값(`input`)도 들어 있다. **세 필드만 골라** 비밀번호 등 원본 값이 응답에 노출되지 않게 한다

### 인증·권한 오류 코드

| 상태 | 오류 코드 | 상황 |
|------|-----------|------|
| 401 | `AUTHENTICATION_REQUIRED` | 인증 정보 없음 |
| 401 | `INVALID_CREDENTIALS` | 로그인 정보 불일치 |
| 401 | `INVALID_TOKEN` | 토큰 검증 실패 또는 사용자 없음 |
| 403 | `POST_FORBIDDEN` | 다른 사람의 게시글 수정·삭제 |
| 403 | `COMMENT_FORBIDDEN` | 다른 사람의 댓글 수정·삭제 |

`UnauthorizedException`은 `WWW-Authenticate: Bearer` 헤더를 자동 지정하고, 핸들러가 `exc.headers`를 응답에 실어 보냅니다.

| | 401 Unauthorized | 403 Forbidden |
|---|------------------|---------------|
| 뜻 | **누구인지 모름** (인증 실패) | 누구인지는 알지만 **권한 없음** |
| 해결 | 로그인·토큰 재발급 | 다시 로그인해도 안 됨 |

### 서버 오류 (500)

예상하지 못한 예외는 `INTERNAL_SERVER_ERROR` 코드와 **공통 메시지**로만 응답하고, 상세 예외와 traceback은 **서버 로그**에만 남깁니다 (내부 구조 노출 방지). 응답 데이터가 `response_model`에 맞지 않는 오류도 서버 오류로 처리됩니다.

## 동작 확인 (`/docs`)

- 회원가입 응답의 회원 정보가 `data`에, 회원가입·생성·수정 응답의 안내 문구가 `message`에 담긴다
- 로그인 응답의 `data.access_token`을 **Authorize**에 입력한다
- 게시글 목록은 `data` 배열, 상세는 `data` 객체
- 없는 게시글 조회 → 404 + `POST_NOT_FOUND`
- 필수 입력값 누락 → 422 + 오류 위치 목록
- 삭제 성공 → 200, `data: null`, `message`는 삭제 안내 문구
