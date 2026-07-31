# URL 구조

URL(Uniform Resource Locator)은 인터넷 상의 자원 위치를 나타내는 주소 체계입니다.

## 전체 구조

```
https://user:pass@www.example.com:8080/products/item?id=42&sort=asc#reviews
└─┬──┘   └──┬───┘ └───────┬───────┘└─┬─┘└─────┬──────┘└──────┬──────┘└──┬───┘
scheme  userinfo       host        port      path          query    fragment
       └──────────────────┬──────────────────┘
                       authority
```

## 구성 요소

| 구성 요소 | 설명 | 예시 |
|-----------|------|------|
| **scheme(프로토콜)** | 자원에 접근하는 방식/프로토콜 | `http`, `https`, `ftp`, `mailto` |
| **userinfo** | 접속 계정 정보 (거의 사용 안 함, 노출 위험) | `user:pass@` |
| **host** | 서버의 도메인 이름 또는 IP 주소 | `www.example.com` |
| **port** | 서버의 포트 번호 (생략 시 프로토콜 기본값 사용) | `:8080`, https는 기본 443 |
| **path** | 서버 내 자원의 경로 | `/products/item` |
| **query** | 서버에 전달하는 추가 파라미터 (`key=value`를 `&`로 연결) | `?id=42&sort=asc` |
| **fragment** | 문서 내 특정 위치를 가리키는 조각 식별자. 서버로 전송되지 않고 브라우저에서만 처리됨 | `#reviews` |

## authority

scheme 뒤 `//` 다음부터 path 앞까지를 authority라고 부르며, `userinfo@host:port`로 구성됩니다.

## 참고

- **query는 서버로 전송**되지만 **fragment는 서버로 전송되지 않는다** — 서버 로그에 남기고 싶지 않은 정보를 query에 넣으면 안 되는 이유이기도 함.
- 포트를 생략하면 scheme의 기본 포트(http=80, https=443)를 사용한다.
- URL에 한글/특수문자를 넣으면 퍼센트 인코딩(예: 공백 → `%20`)으로 변환된다.

## URL vs URI vs URN

- **URI**: 자원을 식별하는 모든 방법을 포괄하는 상위 개념
- **URL**: URI 중에서 자원의 **위치**를 나타내는 것 (`https://...`)
- **URN**: URI 중에서 자원의 **이름**만으로 식별하는 것 (위치와 무관, 예: `urn:isbn:0451450523`)
