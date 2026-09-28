# virtual-financial-services 배포 기록 (2026-09-28) — 첫 DB 연동 웹앱

[langgraph_mini](https://github.com/jjh7757/langgraph_mini) 프로젝트(LangGraph 기반
은행 업무 에이전트, 조회/이체/카드/청구서 + interrupt 기반 승인 흐름)를 JSON 파일
저장소에서 Postgres/Redis로 옮기고, 처음으로 이 배포 환경에 웹으로 올린 기록.
[새 앱 배포 절차](새앱배포절차.md)·[DB환경구성.md](DB환경구성.md)를 실제로 따라가며
검증하는 목적도 있었다 — **공용 DB에 database/index를 붙이는 게 처음 실전에서 검증된
사례**다(그 전까지 "사용 중인 앱: 아직 없음"이었음).

결과: **https://virtual-financial-services.ai-agent-develop.cloud/chat** — 저장소
[jjh7757/langgraph_mini](https://github.com/jjh7757/langgraph_mini)

## 절차대로 갔을 때 실제로 걸린 것

### `deploy.yml` 템플릿을 그대로 복사하면서 브랜치를 안 바꿨다

```yaml
on:
  push:
    branches: [master]   # 템플릿 그대로 — 이 저장소 기본 브랜치는 main
```

`git push`를 몇 번을 해도 워크플로 자체가 안 떴다. **브랜치 이름은 새 앱마다 확인해야 할
플레이스홀더**라는 걸 다시 확인 — 템플릿에 있는 값이라고 다 맞는 게 아니다(구축기록.md의
"콘솔 마법사가 만들어준 값이라고 맞다는 보장이 없다"와 같은 종류의 함정).

### 이 환경에 Terraform 바이너리가 없었다

ECR 리포지토리+수명주기 정책, IAM 신뢰 정책 추가를 Terraform으로 관리하려 했는데
정작 실행 환경(샌드박스)에 `terraform` CLI가 없었다. `aws ecr`/`aws iam` CLI로 직접
만들어서 **선언하려던 것과 동일한 리소스**를 먼저 만들고, `.tf` 파일과 `terraform import`
명령을 코드 저장소에 같이 남겨서 나중에 terraform을 설치하면 state로 편입할 수 있게만
해뒀다. IAM 신뢰 정책 쪽은 애초에 Terraform으로 안 넣기로 했다 — `assume_role_policy`는
AWS API상 "한 줄만 추가"가 안 되고 전체 문서를 통째로 관리해야 해서, `deploy-test`/`rag`가
쓰던 기존 신뢰 정책의 소유권을 지금 옮기는 리스크가 이득보다 크다고 판단했다.

## 배포 직후 컨테이너가 바로 죽었다

`GOOGLE_API_KEY`를 아직 안 채운 상태로 첫 배포를 해보니, 그 값이 없으면
`ChatGoogleGenerativeAI` 생성자가 예외를 던지는데 이걸 앱 시작(lifespan) 안에서
그대로 하고 있어서 **컨테이너 전체가 크래시 루프**에 빠졌다(헬스체크도 응답 못 함).

키가 없어도 헬스체크·정적 페이지는 살아있고, 채팅 엔드포인트만 503으로 안내하도록
고쳤다. **의존성이 아직 준비 안 된 상태를 "앱이 죽는 것"이 아니라 "그 기능만 비활성"으로
다루는 게, 최소한 헬스체크·모니터링 관점에서는 항상 더 안전하다** — rag 앱도 인덱스가
아직 준비 안 됐을 때 `/health`는 200을 주고 질의만 503으로 막는 것과 같은 패턴이다.

## 헬스체크가 계속 `unhealthy`였다

```yaml
healthcheck:
  test: ["CMD", "wget", "-qO-", "http://localhost:8000/"]
```

기존 앱들과 똑같은 템플릿인데, 이 앱의 베이스 이미지(`ghcr.io/astral-sh/uv:python3.13-
bookworm-slim`)엔 **`wget`이 없었다.** `docker inspect`의 헬스체크 로그를 보고서야
`exec: "wget": executable file not found in $PATH`를 확인했다.

```yaml
test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"]
```

파이썬 앱이면 파이썬 표준 라이브러리로 헬스체크하는 게 베이스 이미지가 뭐든 안전하다.
**같은 `docker-compose.yml` 템플릿이라도 베이스 이미지가 바뀌면 안의 유틸리티 존재
여부를 다시 확인해야 한다** — 이후로 slim/distroless 계열 이미지를 쓸 때는 헬스체크부터
점검할 것.

## Redis 연결이 `localhost:3`으로 시도됐다 — URL 인코딩 문제

가장 오래 걸린 문제. 서버 `.env`에 `GOOGLE_API_KEY`까지 채우고 재시작한 뒤 처음 대화를
걸어보니 500 에러:

```
redis.exceptions.ConnectionError: Error 111 connecting to localhost:3. Connection refused.
```

`REDIS_URL`을 `redis://:{공용 비밀번호}@redis:6379/0` 형태로 조립했는데, 그 비밀번호가
`openssl rand -base64`로 생성된 값이라 `/`, `+`, `=` 같은 **URL에서 의미를 갖는 문자를
그대로 포함**하고 있었다. 인코딩 없이 넣으면 redis-py의 URL 파서가 `/`를 경로 구분자로
오인해서 `host:port`를 엉뚱하게 잘라버린다(`localhost:3`이 그 결과).

```python
import urllib.parse
encoded = urllib.parse.quote(password, safe="")
```

로 인코딩해서 재작성하니 정상 연결됐다. **[DB환경구성.md](DB환경구성.md)의 "새 프로젝트에
DB 붙이기" 절차대로 공용 비밀번호를 접속 문자열에 넣을 때는 항상 URL 인코딩을 거칠 것** —
`openssl rand -base64`가 만드는 문자셋 자체가 URL에 안전하지 않다. 다음 앱을 붙일 때도
같은 함정이 있다.

## 검증

```
{"status":"ok"}                                   # GET /
```

| 항목 | 결과 |
|---|---|
| HTTPS | `200`, Let's Encrypt 인증서 발급 확인 |
| 실제 대화(조회) | "내 계좌 목록이랑 잔액 보여줘" → 정상 응답 |
| 실제 대화(승인 실행) | 이체 제안 → "응 진행해"(자연어 승인) → 실행 |
| DB 반영 확인 | Postgres에 직접 접속해 잔액 변경(490,000→~) 확인 |

LLM 에이전트 자체(tool 22개 bind 시 응답이 비는 문제, 시스템 프롬프트의 중복 확인
질문 등)에서도 버그가 몇 개 더 나왔는데, 이건 AWS 환경보다는 앱 쪽 문제라 자세한 건
[langgraph_mini의 진행상황.md](https://github.com/jjh7757/langgraph_mini/blob/main/설계초안/진행상황.md)에
남겨뒀다.

## `monitor.sh`에 새 앱 체크를 처음엔 빼먹었다

배포·DNS·헬스체크까지 다 확인해놓고 정작 `/srv/monitor.sh`(5분마다 도는 헬스 체크
스크립트)에 이 앱을 추가하는 걸 잊었다 — `rag` 철거 때는 체크를 **빼는** 것까지
했으면서, 새로 추가할 때 체크를 **넣는** 걸 대칭으로 챙기지 못한 것.

```bash
check_url "virtual-financial-services" "https://virtual-financial-services.ai-agent-develop.cloud"
check_container_health "virtual-financial-services"
```

두 줄을 추가하면서 또 하나 걸렸다 — 로컬에서 파일을 읽고 다시 써서 서버로 올리는
과정에서 줄바꿈이 **CRLF로 바뀌어** 스크립트가 아예 안 돌았다(`$'\r': command not found`).
`tr -d '\r'`로 정리하고 나서야 정상화됐다. **텍스트 파일을 로컬 편집 → 서버 업로드로
왕복시킬 때는 줄바꿈 형식을 항상 의심할 것**(Windows 환경에서 특히).

**교훈: 앱을 내릴 때 체크리스트가 있으면, 앱을 올릴 때도 대칭인 체크리스트가 있어야
한다.** [새앱배포절차.md](새앱배포절차.md)의 체크리스트에 "monitor.sh에 앱 체크 추가"를
넣어두는 게 나을 것 같다.

## 정리

- **템플릿·절차 문서가 실전에서 대부분 통했다** — DB환경구성.md의 "새 프로젝트에 DB
  붙이기" 6단계 자체는 그대로 맞았고, 문제는 전부 "값을 안 바꿈"(브랜치명) 또는
  "환경이 달라짐"(베이스 이미지에 wget 없음, 비밀번호에 URL 특수문자)에서 나왔다.
- **공용 Postgres/Redis에 두 번째 앱을 붙여보고서야 드러난 문제**(Redis URL 인코딩)가
  있었다 — `rag`가 이미지 크기로 파이프라인의 사각지대를 드러냈던 것과 같은 종류로,
  "처음 앱으로 검증한 절차는 다음 앱에서 처음 깨진다."
- 이 환경에 Terraform이 없다는 것도 이번에 처음 확인했다 — 다음에 인프라 자동화를
  더 쓰려면 이 샌드박스에 terraform 설치부터 필요.
