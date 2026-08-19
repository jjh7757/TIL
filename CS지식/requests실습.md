# requests로 API 호출하기

[API 기초](API기초.md)에서 정리한 요청 구조(엔드포인트·메서드·헤더·바디)를 파이썬에서 실제로 다루는 라이브러리가 `requests`다.

```bash
pip install requests
```

## HTTP 메서드별 사용법

| 메서드 | 용도 |
|---|---|
| `requests.get(url)` | 데이터나 목록 조회 |
| `requests.post(url, json=data)` | 새 데이터 생성 |
| `requests.patch(url, json=data)` | 기존 데이터 일부만 수정 |
| `requests.put(url, json=data)` | 기존 데이터 전체 교체 |
| `requests.delete(url)` | 데이터 삭제 |

```python
import requests

# 단일 리소스 조회
response = requests.get("https://jsonplaceholder.typicode.com/posts/10")
print(response.json()['body'])

# 생성
response = requests.post(
    "https://jsonplaceholder.typicode.com/posts",
    json={"title": "제목", "body": "내용", "userId": 1},
)
print(response.status_code, response.json())
```

모든 메서드는 `Response` 객체를 반환한다. 응답 본문은 `response.json()`, 성공 여부는 `response.status_code` 또는 `response.raise_for_status()`로 확인한다.

## 요청 옵션 — params / headers

- `params`: URL 뒤에 붙는 쿼리 매개변수. `requests.get(url, params={"userId": 2})` → `?userId=2`가 자동으로 붙는다.
- `headers`: 인증 토큰 등 메타데이터. `headers={"Authorization": "Bearer <token>"}`

```python
params = {"userId": 2}
response = requests.get("https://jsonplaceholder.typicode.com/posts", params=params)
print(len(response.json()))   # 해당 유저의 게시글 수
```

## 예외 처리

- `Timeout`: `timeout` 인자로 지정한 시간 안에 응답이 오지 않을 때
- `HTTPError`: 서버 응답이 4xx/5xx일 때 — `raise_for_status()`를 호출해야 실제로 발생한다. 호출하지 않으면 500이 와도 예외 없이 `response.status_code`에만 담긴다
- `RequestException`: 위 예외들을 포함하는 상위 예외 — 세분화가 필요 없을 때 사용

```python
try:
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    print(response.json())
except requests.exceptions.Timeout:
    print("요청 시간이 초과되었습니다.")
except requests.exceptions.HTTPError as error:
    print("HTTP 오류가 발생했습니다:", error)
except requests.exceptions.RequestException as error:
    print("요청 중 오류가 발생했습니다:", error)
```

[예외 처리](파이썬기초/14_예외처리.md)에서 다룬 `try`/`except`/`as` 구조가 그대로 적용된다 — 다만 무엇을 `except`로 잡을지가 `requests`가 정의한 예외 계층을 아는 것에 달려 있다는 점이 다르다.

## 참고

- [API 기초](API기초.md)
- [예외 처리](파이썬기초/14_예외처리.md)
