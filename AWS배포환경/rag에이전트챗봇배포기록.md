# RAG 에이전트 챗봇 배포 기록 (2026-10-16)

부트캠프 실습으로 만든 **Supervisor + 분야별 서브 에이전트 RAG 챗봇**(Streamlit)을 이 배포 환경에 올린 기록.
[새 앱 배포 절차](새앱배포절차.md) 7단계를 그대로 따랐고, 이번에는 AWS CLI와 Claude Code로 단계 대부분을 진행했다.

결과: **https://chatbot.ai-agent-develop.cloud** — 저장소 [jjh7757/rag-agent-practice](https://github.com/jjh7757/rag-agent-practice)

금융·공공·의료·법률·커머스 PDF에 질문하면, 안내 데스크(supervisor)가 주제에 맞는 분야 상담원(서브 에이전트)에게
위임하고 여러 분야에 걸치면 답을 모아 정리한다. 답변 아래에 인용한 쪽의 그래프·그림과 출처, 위임 내역을 보여준다.

## 올리기 전에 정한 것

### 실습 폴더를 그대로 올리지 않고 런타임에 필요한 것만 골랐다

실습 폴더에는 평가 스크립트, 실험 단계마다 백업한 `chroma_db_before_*` 폴더 10여 개, 원본 PDF(171MB)가 섞여 있었다.
서비스에 필요한 건 `app.py`·`supervisor_agent.py`·`hybrid_search.py`, 벡터 DB(`chroma_db`), 그림(`figures`),
BM25 토큰 캐시(`_bm25_tokens.pkl`)뿐이라 이것만 새 저장소로 옮겼다. 총 365MB.

### 인덱스를 이미지에 포함했다

이전 rag 앱은 기동 때 임베딩을 만들어 볼륨에 저장했지만, 이번에는 **로컬에서 만든 벡터 DB를 이미지에 넣었다.**
서버에서 임베딩을 다시 만들면 API 호출이 낭비되고, `build_index.py`가 서버에 필요 없는 의존성(PDF 파서 등)을 끌고 오기 때문이다.
대신 문서가 바뀌면 이미지를 다시 빌드해야 한다 — 문서가 고정된 실습 데이터라 감수할 만하다고 판단했다.

### 파일 크기 제한

GitHub은 100MB가 넘는 파일을 거부하고 50MB가 넘으면 경고한다. 가장 큰 `data_level0.bin`이 68MB라 일반 push로 통과했다
(Git LFS 불필요). 푸시 전에 `find -size +50M`로 확인했다.

### 포트는 Streamlit 기본 8501

[포트를 세 군데서 맞춘다](새앱배포절차.md): 앱(`--server.port=8501`) / compose `expose`·healthcheck / Caddyfile `reverse_proxy rag-agent-practice:8501`.

## 절차대로 갔을 때

### 헬스체크는 wget 대신 파이썬으로

[virtual-financial-services 배포](virtual-financial-services배포기록.md)에서 `wget` 없는 slim 이미지 때문에 헬스체크가 계속 실패했다.
이번에는 같은 실수를 하지 않으려고 `python -c "urllib.request.urlopen(...)"`로 `/_stcore/health`를 확인하게 했다.

### 메모리 상한은 이전 앱 기준으로

이전 rag 앱의 실사용이 667MB였으므로 상한을 900MB로 잡았다. 배포 직후 유휴 상태 **371MiB**,
서버 전체 available은 약 1.2GB였다. 질문 처리 중 최대치는 아직 측정하지 않았다.

### IAM 신뢰 정책은 AWS CLI로 한 줄만 추가

`github-actions-deploy`의 `sub` 목록에 `repo:jjh7757@307797437/rag-agent-practice@<repo_id>:*`를 추가했다.
`assume_role_policy`는 한 줄만 추가하는 API가 없어서 **현재 문서를 받아 항목을 덧붙인 뒤 통째로 다시 올려야** 한다.
기존 항목이 그대로 남았는지 적용 뒤에 다시 읽어서 확인했다.

### 첫 push에서 파이프라인이 한 번에 통과했다

ECR(Mutable + 5개 보관) → IAM → 서버 디렉토리·`.env` → DNS 전파 확인 → Caddy 블록 → push 순서를 지켰다.
Caddy는 `caddy validate`로 설정을 검증한 뒤 reload했고, DNS는 `nslookup chatbot... 8.8.8.8`로 A 레코드가
보이는 것을 확인한 뒤에 reload했다. 순서를 지킨 덕에 인증서 발급 실패 없이 한 번에 HTTPS 200이 나왔다.

## 검증

| 항목 | 결과 |
|---|---|
| HTTPS | 200 |
| `/_stcore/health` | 200 |
| 컨테이너 메모리(유휴) | 371MiB / 900MiB |
| 실제 질문 | 사용자가 화면에서 직접 확인 — 답변 정상 |

## 아직 남은 것

- `/srv/monitor.sh`에 이 앱의 `check_url`/`check_container_health` 추가 ([새 앱 배포 절차](새앱배포절차.md) 체크리스트 마지막 항목)
- 질문이 몰릴 때의 메모리 최대치 측정
- 공개 URL이라 질문 한 번이 곧 Gemini API 호출인데, 이번 앱에는 요청 제한을 넣지 않았다(이전 rag-web에는 있었음)
