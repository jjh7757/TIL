# FastAPI 실습 과제 — 회원가입·로그인과 위시리스트

`fastapi_ai/fastapi_prac`의 상품 관리 API에 **회원가입·로그인**과 **개인 위시리스트**를 추가하는 과제의 요구사항 정리입니다. 구현에 쓰이는 개념은 [다대다 관계](FastAPI_다대다관계.md), [공통 응답과 예외 처리](FastAPI_공통응답_예외처리.md), [비동기 CRUD](FastAPI_비동기CRUD.md)에 정리되어 있습니다.

## 1. 회원

### User 모델 (`users`)

| 필드 | 타입 | 조건 |
|------|------|------|
| `id` | int | 자동 생성 기본키 |
| `email` | str | 최대 254자, **중복 불가**, 필수 |
| `hashed_password` | str | 비밀번호 해시, 필수 |
| `created_at` | datetime | 가입 시각, **DB에서 자동 생성** (`server_default=func.now()`) |

- 이메일은 **형식 검증** 후 **소문자로** 저장·조회 (`Foo@A.com`과 `foo@a.com`은 같은 회원)
- 회원가입 비밀번호는 **15~128자**, **Argon2id**로 해싱해 저장 (`pwdlib[argon2]`)
- 응답에는 비밀번호와 해시를 **절대 포함하지 않음** → 응답 스키마에서 필드 자체를 빼기

### 인증 API

| 메서드 | URL | 요청 본문 | 응답 | 성공 |
|--------|-----|-----------|------|------|
| POST | `/auth/signup` | email, password | id, email, created_at | 201 |
| POST | `/auth/login` | email, password | access_token, `token_type: "bearer"` | 200 |
| GET | `/me` | 없음 | 인증된 사용자의 id, email, created_at | 200 |

- 로그인 비밀번호는 **1~128자** (가입 규칙과 다름: 로그인은 "맞는지"만 확인하므로 길이 규칙을 강제하지 않음)
- JWT 페이로드

| 클레임 | 값 |
|--------|-----|
| `sub` | 사용자 ID를 **문자열로** (JWT 표준상 `sub`는 문자열) |
| `iat` | 발급 시각 |
| `exp` | 만료 시각 |

- 인증이 필요한 요청은 `Authorization: Bearer <access_token>` 헤더 사용

### 오류 규칙

| 상황 | 상태 코드 |
|------|-----------|
| 중복 이메일로 가입 | 409 |
| 가입 안 된 이메일 / 잘못된 비밀번호로 로그인 | 401 (둘을 구분하지 않음 → 이메일 가입 여부 노출 방지) |
| 요청 값이 조건에 맞지 않음 | 422 |
| `/me`: 토큰 없음·유효하지 않음·토큰의 사용자가 없음 | 401 |

## 2. 상품 위시리스트

로그인한 사용자가 **기존 상품**을 자신의 위시리스트에 담고 조회·삭제합니다.

### WishlistItem 모델 (`wishlist_items`)

| 필드 | 타입 | 조건 |
|------|------|------|
| `id` | int | 자동 생성 기본키 |
| `user_id` | int | `users.id` 외래키, 필수 |
| `product_id` | int | `products.id` 외래키, 필수 |

- `(user_id, product_id)` 조합은 **고유** → `UniqueConstraint`. 서로 다른 사용자는 같은 상품을 담을 수 있음
- `user_id`는 요청 본문으로 받지 않고 **인증된 사용자의 ID**로 지정 (남의 위시리스트에 담기 방지)
- 사용자–상품 M:N을 연결 테이블로 표현하는 구조 ([다대다 관계](FastAPI_다대다관계.md)와 같은 형태)

### 위시리스트 API (모두 인증 필요)

| 메서드 | URL | 요청 본문 | 기능 | 성공 |
|--------|-----|-----------|------|------|
| POST | `/me/wishlist` | product_id | 상품을 담고 항목의 id, user_id, product_id 반환 | 201 |
| GET | `/me/wishlist` | 없음 | 본인 항목 목록. 항목별 id, product(id, name, final_price, category) | 200 |
| DELETE | `/me/wishlist/{wishlist_item_id}` | 없음 | 본인 항목만 삭제. 상품·다른 사용자 항목은 유지, 본문 없음 | 204 |

### 오류 규칙

| 상황 | 상태 코드 |
|------|-----------|
| 토큰 없음·유효하지 않음·사용자 없음 | 401 |
| 삭제할 항목이 **다른 사용자의 것** | 403 |
| 담을 상품 / 삭제할 항목이 없음 | 404 |
| 같은 상품을 다시 담음 | 400 |
| `product_id`가 양의 정수가 아님 | 422 (`Field(gt=0)`) |
| 담은 상품이 없음 | 200 + 빈 목록 |

- **상품을 삭제하면** 그 상품에 연결된 위시리스트 항목도 함께 삭제 → ORM `cascade="all, delete-orphan"` 또는 FK `ondelete="CASCADE"`

## 구현 체크 포인트

- 삭제는 **존재 확인(404) → 소유자 확인(403)** 순서. 항목이 없으면 소유자를 판단할 수 없다
- 목록 응답에 `product`를 넣으므로 조회 시 상품 관계를 미리 로딩 (`joinedload`, 위시리스트 항목→상품은 N:1) — [N+1 문제](SQLAlchemy_N+1문제.md)
- 중복 담기는 Service에서 먼저 검사(400)하고, DB의 `UniqueConstraint`는 최종 안전장치
