# FastAPI JWT 회원가입과 로그인

이메일·비밀번호로 회원가입하고, 로그인에 성공하면 **JWT access token**을 발급하며, 인증이 필요한 API에는 토큰을 `Authorization` 헤더에 담아 보내는 흐름을 구현했습니다. 인증·JWT 개념은 [인증과 인가](인증과인가.md), 프로젝트 구조는 [FastAPI 레이어드 아키텍처](FastAPI_레이어드아키텍처.md), DB 연동은 [FastAPI DB 연동](FastAPI_DB연동.md)을 참고하세요. 코드는 `fastapi_basic/mysite_auth/`에 있습니다.

## 요청 흐름

```
회원가입:     비밀번호 해싱 → 이메일 중복 확인 → 사용자 저장
로그인:       이메일로 사용자 조회 → 비밀번호 검증 → JWT 발급
내 정보 조회: Bearer 토큰 추출 → JWT 검증 → 사용자 조회 → 응답
```

## API

| 메서드 | 경로 | 기능 | 성공 |
|--------|------|------|------|
| POST | `/auth/signup` | 회원가입 | 201 |
| POST | `/auth/login` | 로그인과 access token 발급 | 200 |
| GET | `/me` | 인증된 사용자 정보 조회 | 200 |

### 인증 관련 파일

| 파일 | 역할 |
|------|------|
| `security.py` | JWT 설정, 비밀번호 해싱·검증, JWT 발급·검증 |
| `dependencies.py` | 요청에서 토큰을 추출하고 인증된 사용자를 전달 |

## 인증 설정

```bash
uv add "pwdlib[argon2]" pyjwt
```

| 라이브러리 | 역할 |
|------------|------|
| `pwdlib[argon2]` | Argon2id 비밀번호 해싱과 검증 |
| `PyJWT` | JWT 생성과 검증 |

### JWT 환경 변수

비밀 키는 터미널에서 생성해 `.env`에 넣는다.

```bash
openssl rand -hex 32
```

```
JWT_SECRET_KEY=생성한_64자리_비밀_키
JWT_EXPIRE_MINUTES=3000
```

- `JWT_SECRET_KEY`: 서명 생성·검증에 쓰는 서버의 **비밀 키**. **저장소에 올리지 않는다.** ([환경변수 관리](환경변수관리.md))
- `JWT_EXPIRE_MINUTES`: 토큰 유효 시간(분). 실습에서는 로그인을 반복하지 않으려고 3000분으로 길게 잡았다. (운영에서는 짧게)

```python
# security.py
load_dotenv(Path(__file__).with_name(".env"))

JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
```

- 처음 import할 때 **한 번만** 실행되므로 `.env`를 수정하면 서버를 재시작한다.
- `os.environ["JWT_SECRET_KEY"]`는 값이 없으면 `KeyError`로 **바로 실패**한다. 비밀 키 없이 서버가 뜨는 것을 막는다.

## 회원가입

### 사용자 모델

`user_auth` 테이블에 이메일과 **비밀번호 해시**를 저장한다. 이메일에는 `UNIQUE` 제약을 둔다.

```python
class User(Base):
    __tablename__ = "user_auth"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- `DateTime(timezone=True)`: PostgreSQL에서 **시간대가 있는** 시각을 쓴다. `server_default=func.now()`: 행을 만들 때 **DB가** 생성 시각을 넣는다.

### 요청·응답 스키마

```python
class UserCreate(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=15, max_length=128, repr=False)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

- 응답(`UserResponse`)에는 **비밀번호·해시 필드가 없다.** (`from_attributes=True`로 ORM 객체에서 변환)
- `repr=False`: 요청 모델을 출력(로그)할 때 비밀번호가 **찍히지 않게** 한다.
- 비밀번호는 가입 시 **15자 이상**을 요구한다. (로그인 요청은 1자 이상으로 받는다. 가입 때 규칙을 검사하고, 로그인은 저장된 해시와의 일치 여부만 본다)

### 비밀번호 해싱

```python
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)
```

- **Argon2id**는 비밀번호 추측에 필요한 **연산·메모리 비용을 높인** 해시 알고리즘이다. `PasswordHash.recommended()`가 Argon2id 해시 객체를 만든다.
- **무작위 salt**를 쓰므로 같은 비밀번호도 해싱 결과가 매번 다르다.
- 해시는 **복호화되지 않는다.** 원문을 되살리는 것이 아니라 "일치하는지"만 검증한다.

### 회원가입 처리

```python
def signup(self, db: Session, data: UserCreate) -> User:
    email = str(data.email).lower()
    hashed_password = hash_password(data.password)

    with db.begin():
        if user_repository.find_by_email(db, email) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 등록된 이메일입니다.",
            )
        user = User(email=email, hashed_password=hashed_password)
        user_repository.save(db, user)

    return user
```

- 이메일을 **소문자로 통일**해 저장한다. (이 앱은 대소문자를 구분하지 않음)
- 해싱은 `with db.begin():` **앞**에서 한다. 비용이 큰 연산 동안 DB 트랜잭션을 열어 두지 않을 수 있다.
- 중복이면 **409 Conflict**.

## 로그인과 토큰 발급

### 요청·응답

```python
class UserLogin(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128, repr=False)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
```

- `Literal["bearer"]`: `token_type` 값을 `"bearer"`로 **제한**한다.
- Bearer 방식에서는 **토큰을 가진 사람이 인증 요청을 보낼 수 있다.** 토큰을 비밀번호처럼 보호해야 한다.

### 비밀번호 검증

입력 비밀번호를 **새로 해싱해 저장된 문자열과 비교하면 salt 때문에 일치하지 않는다.** `verify()`는 저장된 해시의 salt와 매개변수를 이용해 검증하고 `True`/`False`를 반환한다.

```python
def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return password_hash.verify(password, hashed_password)
    except UnknownHashError:
        return False
```

- 저장된 해시 형식을 **인식할 수 없는 경우에도 `False`**(인증 실패)로 처리한다.

### JWT 발급

```python
ALGORITHM = "HS256"

def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)
```

| claim | 의미 | 값 |
|-------|------|-----|
| `sub` | 사용자 식별자 | 사용자 ID를 **문자열**로 변환 |
| `iat` | 발급 시각 | 현재 UTC 시각 |
| `exp` | 만료 시각 | 발급 시각 + 유효 시간 |

- PyJWT가 시각을 숫자 타임스탬프로 변환한다.
- payload는 **암호화되지 않으므로** 비밀번호나 비밀 키를 넣지 않는다.

### 로그인 처리

```python
def login(self, db: Session, data: UserLogin) -> str:
    email = str(data.email).lower()
    with db.begin():
        user = user_repository.find_by_email(db, email)
        if user is None or not verify_password(data.password, user.hashed_password):
            raise authentication_error("이메일 또는 비밀번호가 올바르지 않습니다.")

        user_id = user.id

    return create_access_token(user_id)
```

- **이메일이 없을 때와 비밀번호가 틀렸을 때 같은 401 응답**을 준다. 응답이 다르면 "가입된 이메일인지"가 노출되기 때문이다.
- 트랜잭션 안에서 `user.id`를 변수로 꺼내 두고, 토큰 발급은 밖에서 한다.

### 라우터

```python
router = APIRouter(prefix="/auth", tags=["mysite_auth"])

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(data: UserCreate, db: Annotated[Session, Depends(get_db)]):
    return auth_service.signup(db, data)

@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Annotated[Session, Depends(get_db)], response: Response):
    access_token = auth_service.login(db, data)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return TokenResponse(access_token=access_token)
```

- `db: Annotated[Session, Depends(get_db)]`: `Session`은 매개변수의 **타입**, `Depends(get_db)`는 세션을 제공하는 **의존성** 지정이다.
- `Response` 매개변수로 응답 헤더를 설정한다. `Cache-Control: no-store`는 **토큰 응답을 캐시에 저장하지 않도록** 지시한다.

## 토큰으로 사용자 인증

### 인증 실패 응답

```python
def authentication_error(
    detail: str = "유효하지 않거나 만료된 토큰입니다.",
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
```

- `WWW-Authenticate: Bearer` 헤더로 클라이언트에 **필요한 인증 방식**을 알린다.

### JWT 검증

```python
def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "iat", "exp"]},
        )
        return int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise authentication_error() from None
```

- `algorithms=[ALGORITHM]`: 서버가 허용하는 알고리즘을 **고정**한다. (토큰 헤더가 주장하는 알고리즘을 그대로 믿지 않는다)
- `require`: `sub`, `iat`, `exp`가 **없는 토큰은 거부**한다. 서명·만료도 함께 검증된다.
- 검증한 `sub`를 정수로 바꾸고, JWT 검증이나 정수 변환이 실패하면 **401**.
- `from None`: 내부 예외 정보를 응답에 이어 붙이지 않는다.

### 토큰의 사용자 조회

```python
def get_current_user(self, db: Session, token: str) -> User:
    user_id = decode_access_token(token)
    user = user_repository.find_by_id(db, user_id)
    if user is None:
        raise authentication_error()
    return user
```

- **토큰이 유효해도 사용자가 삭제됐다면 인증에 실패**한다. (JWT는 "발급 당시"의 증명이므로 DB로 한 번 더 확인)

### 인증 의존성

클라이언트는 인증이 필요한 요청마다 다음 헤더를 보낸다.

```
Authorization: Bearer <access_token>
```

```python
bearer_scheme = HTTPBearer(bearerFormat="JWT", auto_error=False)

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserResponse:
    if credentials is None:
        raise authentication_error("로그인이 필요합니다.")
    with SessionLocal() as db:
        user = auth_service.get_current_user(db, credentials.credentials)
        return UserResponse.model_validate(user)
```

- `HTTPBearer`는 헤더에서 토큰을 추출하고 **Swagger UI에 인증 입력창**을 만든다. 실제 JWT 검증은 `auth_service.get_current_user()`가 호출하는 보안 함수가 한다.
- `credentials.scheme`은 `"Bearer"`, `credentials.credentials`는 `Bearer ` 접두사를 뺀 **실제 JWT 문자열**이다.
- `auto_error=False`: 헤더가 없거나 Bearer 형식이 아니면 `credentials`가 `None`이 되어 **직접 401**을 반환할 수 있다. (기본값이면 FastAPI가 403을 반환)
- 인증 조회는 **별도 `SessionLocal()`**을 쓴다. 세션이 열려 있는 동안 `UserResponse.model_validate(user)`로 ORM 객체를 Pydantic 모델로 바꾸고 세션을 닫는다.
- **세션을 분리하는 이유**: 같은 DB 세션에서 인증 조회가 먼저 트랜잭션을 시작하면 Service의 `with db.begin():`과 **충돌**할 수 있기 때문이다. 인증 조회와 쓰기 작업의 세션을 나눈다.

### 내 정보 조회

```python
@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[UserResponse, Depends(get_current_user)]):
    return current_user
```

- `current_user: Annotated[UserResponse, Depends(get_current_user)]`를 선언하면 **라우터가 실행되기 전에 인증**을 거치고, 반환된 사용자 정보를 전달받는다.

## 실행과 확인

```bash
uv run fastapi dev main.py
```

`http://127.0.0.1:8000/docs`의 `mysite_auth` 그룹에서 확인한다. 토큰은 `Depends(get_current_user)`를 쓰는 API에만 필요하다.

1. `POST /auth/signup`에 `{"email": "...", "password": "(15자 이상)"}` → **201**과 `id`, `email`, `created_at`
2. 같은 JSON으로 `POST /auth/login` → `{"access_token": "...", "token_type": "bearer"}`
3. 응답의 `access_token`을 복사해 화면 상단 **Authorize**의 Value에 **토큰만** 입력한다. (`Bearer ` 접두사는 Swagger가 붙임)
4. Authorize를 누르고 창을 닫은 뒤 `GET /me` 실행
5. Authorize → Logout으로 토큰을 지우고 다시 `/me` → **401**

### 실패 응답

| 요청 | 상태 코드 |
|------|-----------|
| 같은 이메일로 다시 회원가입 | 409 |
| 이메일 형식·비밀번호 길이가 조건을 벗어난 요청 | 422 |
| 가입되지 않은 이메일 또는 틀린 비밀번호로 로그인 | 401 |
| 토큰 없이 `/me` 요청 | 401 |
| 변조·만료·필수 claim 누락 토큰으로 `/me` 요청 | 401 |
| 삭제된 사용자의 토큰으로 `/me` 요청 | 401 |

## 정리

- 비밀번호는 **해시(Argon2id + salt)**로만 저장하고, 로그인 때는 `verify()`로 비교한다.
- 로그인 실패 응답은 이메일 없음과 비밀번호 불일치를 **구분하지 않는다.**
- JWT는 `sub`·`iat`·`exp`를 담아 HS256으로 서명하고, 검증 때는 **허용 알고리즘 고정 + 필수 claim 요구**로 읽는다.
- 인증은 **의존성(`Depends(get_current_user)`)**으로 라우터 앞에서 처리한다. 토큰이 유효해도 사용자가 존재하는지 DB로 확인한다.
- 인증 조회와 쓰기 트랜잭션의 **DB 세션을 분리**한다.
