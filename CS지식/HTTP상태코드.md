# HTTP 상태 코드 (Status Code)

수업 중 손글씨 판서를 정리한 내용입니다. [HTTP 기초](HTTP기초.md)의 상태 코드 부분을 더 자세히 다룹니다.

## 응답(Response)의 구성

서버가 클라이언트에게 돌려주는 **Response**는 크게 두 부분으로 구성됩니다.

- **Status Code(상태 코드)** — 요청이 어떻게 처리됐는지 나타내는 세 자리 숫자
- **Data(Body)** — 실제로 돌려주는 데이터

## 상태 코드 5가지 분류

| 분류 | 의미 | 대표 예시 |
|------|------|-----------|
| **1XX** | 정보성(Informational) — 요청을 받았고 처리 중 | 100 Continue |
| **2XX** | **Successful responses** — 성공, 문제 없음 | 200 OK, 201 Created |
| **3XX** | Redirection(리다이렉션) — 요청한 자원이 다른 위치에 있음 | 301 Moved Permanently, 302 Found |
| **4XX** | **Client Error Responses** — 클라이언트 쪽 요청에 문제가 있음 | 400 Bad Request, 404 Not Found |
| **5XX** | Server Error — 서버 쪽에서 처리 중 문제가 발생 | 500 Internal Server Error |

## 리다이렉션(3XX) 개념

그림에서는 자원 `A`가 화살표를 통해 `A'`(다른 위치)로 이어지는 것으로 표현되어 있습니다. 클라이언트가 요청한 자원이 실제로는 다른 위치로 옮겨졌을 때, 서버가 "그 주소로 가서 다시 요청해라"라고 알려주는 것이 3XX 응답의 역할입니다.

## 주요 코드 예시

- **200 OK** — 요청이 정상적으로 처리됨
- **201 Created** — 요청으로 새 리소스가 생성됨
- **400 Bad Request** — 요청 형식/내용에 문제가 있음
- **404 Not Found** — 요청한 자원을 찾을 수 없음

## 정리

Response는 **Status Code + Data(Body)**로 이루어지고, Status Code는 1XX~5XX 다섯 계열로 나뉘어 각각 정보성/성공/리다이렉션/클라이언트 오류/서버 오류라는 응답의 성격을 나타냅니다.
