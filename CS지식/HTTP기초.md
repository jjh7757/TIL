# HTTP 기초

HTTP(HyperText Transfer Protocol)는 클라이언트와 서버가 자원을 주고받을 때 쓰는 **요청-응답 기반** 프로토콜입니다.

## 요청(Request) 구조

```
GET /products/item?id=42 HTTP/1.1
Host: www.example.com
User-Agent: Mozilla/5.0
Accept: application/json

(body — GET에는 보통 없음)
```

- **요청 라인**: 메서드 + 경로(+ 쿼리) + 프로토콜 버전
- **헤더**: 요청에 대한 부가 정보 (Host, User-Agent, Accept 등)
- **바디**: 서버로 보낼 실제 데이터 (POST/PUT 등에서 주로 사용)

## 응답(Response) 구조

```
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 128

{"id": 42, "name": "item"}
```

- **상태 라인**: 프로토콜 버전 + 상태 코드 + 상태 메시지
- **헤더**: 응답에 대한 부가 정보 (Content-Type, Content-Length 등)
- **바디**: 실제 응답 데이터

## 주요 메서드

| 메서드 | 용도 |
|--------|------|
| GET | 자원 조회 (바디 없음, 캐시 가능) |
| POST | 자원 생성 / 서버에 데이터 제출 |
| PUT | 자원 전체 교체 |
| PATCH | 자원 일부 수정 |
| DELETE | 자원 삭제 |

## 상태 코드

| 대역 | 의미 | 예시 |
|------|------|------|
| 1xx | 정보성 | 100 Continue |
| 2xx | 성공 | 200 OK, 201 Created, 204 No Content |
| 3xx | 리다이렉션 | 301 Moved Permanently, 304 Not Modified |
| 4xx | 클라이언트 오류 | 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found |
| 5xx | 서버 오류 | 500 Internal Server Error, 502 Bad Gateway, 503 Service Unavailable |

## 특징

- **무상태(Stateless)**: 서버는 각 요청을 독립적으로 처리하며, 이전 요청의 상태를 기억하지 않는다. 로그인 유지 같은 상태 관리는 쿠키/세션/토큰으로 별도 구현한다.
- **텍스트 기반**: 헤더는 사람이 읽을 수 있는 텍스트 형태 (HTTP/2부터는 바이너리 프레이밍을 쓰지만 헤더 의미 체계는 동일).
- **HTTPS**: HTTP에 TLS(암호화)를 얹은 것. 기본 포트가 80(HTTP) vs 443(HTTPS)으로 다르다.

## 자주 쓰는 헤더

| 헤더 | 설명 |
|------|------|
| `Content-Type` | 바디 데이터의 형식 (`application/json`, `text/html` 등) |
| `Authorization` | 인증 정보 (`Bearer <token>` 등) |
| `Cookie` / `Set-Cookie` | 클라이언트-서버 간 상태 유지용 데이터 |
| `Cache-Control` | 캐싱 정책 |
