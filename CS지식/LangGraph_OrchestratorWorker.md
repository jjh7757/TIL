# LangGraph Orchestrator-Worker — Send API로 동적 병렬화하기

## 고정 Fan-out과 뭐가 다른가

[LangGraph 병렬 처리](LangGraph_병렬처리.md)의 Fan-out/Fan-in은 그래프를 만드는 시점에 작업 종류와 수가 정해져 있다(법률/재무/기술 노드 3개 고정). Orchestrator-worker 패턴은 **실행 시점에** Orchestrator가 사용자 요청을 분석해서 필요한 작업 개수와 내용을 스스로 계획하고, `Send` API로 그만큼의 Worker를 동적으로 띄운다.

```
START → Orchestrator ─┬→ Worker
                      ├→ Worker ─→ 결과 종합 → END
                      └→ Worker
```

`Send(노드이름, state)`는 지정한 Worker 노드를 **새로운 입력 State로** 실행시키는 객체다. 라우팅 함수가 `Send` 객체의 리스트를 반환하면 그 리스트 길이만큼 동적 Fan-out이 일어난다 — 사용자 요청마다 Worker 수가 3개가 될 수도, 8개가 될 수도 있다는 뜻이다.

## 전체 State vs Worker State

- **`ReportState`**: 그래프 전체가 공유하는 상태. 원본 요청, Orchestrator가 만든 작업 목록, Worker 결과들, 최종 보고서를 담는다.
- **`WorkerState`**: Worker 한 개가 자기 작업을 처리하는 데 필요한 값만 담는다.

Worker들은 전부 같은 `WorkerState` 스키마를 쓰지만, 각 `Send`가 실어 보내는 값은 서로 독립적이다. 예를 들어 `Send("analyze_task", {"task_id": 0, "title": "비용 분석", ...})`와 `Send("analyze_task", {"task_id": 1, "title": "위험 분석", ...})`는 같은 함수를 실행해도 입력이 다르다. 그래서 **Worker는 공유 State를 뒤져서 "내 작업이 뭐였지"를 찾을 필요가 없다** — `Send`가 전달한 State를 그대로 쓰면 된다.

`task_id`는 Worker를 구분하는 값이 아니라, 병렬 실행이 끝나고 하나의 리스트로 합쳐진 결과가 **원래 어느 작업이었는지 식별해서 계획 순서대로 재정렬**하기 위한 값이다. 결과를 모으는 State 필드는 `results: Annotated[list, operator.add]`처럼 reducer를 둬서, 여러 Worker가 각자 반환한 결과를 덮어쓰지 않고 이어붙인다.

## 세 조각: Orchestrator / 라우팅 함수 / Worker

- **`create_plan`(Orchestrator)**: `with_structured_output(AnalysisPlan)`으로 LLM 응답을 `AnalysisTask` 목록으로 받는다. 이 목록의 **길이가 곧 Worker 수**다.
- **`assign_workers`(라우팅 함수)**: 일반 노드가 아니라 조건부 엣지에 연결하는 라우팅 함수다. 계획의 각 작업을 `Send("analyze_task", worker_state)`로 바꿔서 리스트로 반환한다.
- **`analyze_task`(Worker)**: 모든 작업이 공통으로 쓰는 노드. 입력값(WorkerState)만 다르고 로직은 동일하며, 결과 하나를 리스트에 담아 반환한다. 병렬 실행되므로 완료 순서는 계획 순서와 다를 수 있다.
- **`make_report`(Fan-in)**: 병합된 `results`를 `task_id`로 재정렬한 뒤 최종 보고서를 만든다 — 완료 순서에 휘둘리지 않도록.

같은 단계에서 생성된 모든 Worker가 완료될 때까지 LangGraph가 기다린 뒤에야 `make_report`가 실행된다. 즉 Worker 하나가 끝날 때마다 보고서를 조각조각 만드는 게 아니라, 전부 끝난 뒤 한 번에 종합한다. `stream_mode="updates"`로 실행하면 Orchestrator의 계획 → 각 Worker의 완료 → 최종 보고서 생성이 `{노드 이름: 갱신 내용}` 형태로 순서대로(단, Worker 간 순서는 매번 다르게) 찍히는 걸 볼 수 있다.

## Rate Limiting — 동적 병렬화의 대가

Orchestrator가 작업을 5개로 나누면 순식간에 LLM 요청 5개가 동시에 나갈 수 있어서, 순차 실행보다 **Rate Limit에 걸리기 훨씬 쉽다.**

Provider가 흔히 쓰는 제한 기준:

- **RPM** (Requests Per Minute): 분당 요청 수
- **TPM** (Tokens Per Minute): 분당 처리 토큰 수
- **RPD** (Requests Per Day): 일일 요청 수
- **동시 요청 수**: 같은 시점에 처리 가능한 요청 수

한도 초과 시 보통 `429 Too Many Requests`가 뜬다.

**`max_concurrency`**: LangGraph 실행 시 한 번에 동시 수행할 수 있는 태스크 수를 제한하는 설정. 전체 Worker 수를 줄이는 게 아니라, 실행 중인 Worker가 끝나야 대기 중이던 다음 Worker가 시작되는 방식이다 — 예를 들어 주제 8개를 전부 분석하되 최대 3개만 동시에 돌린다. 다만 `max_concurrency`는 순간적으로 요청이 몰리는 걸 완화할 뿐 RPM/TPM을 직접 계산해서 지켜주지는 않으므로, 실제 Rate Limit 대응에는 **재시도 + exponential backoff + 요청 속도 제한**을 같이 써야 한다. 특정 API 호출이나 코드 블록만 제한하고 싶으면 `asyncio.Semaphore`를 쓸 수 있다.

## 실습: 맞춤형 학습 자료 생성

사용자가 목차를 직접 안 주고, Orchestrator가 학습 대상·시간을 고려해서 목차 3~5개를 스스로 정하고, 목차마다 Worker를 동적으로 띄워 설명·예제를 작성한 뒤, 결과를 목차 순서대로 정리해 하나의 학습 자료로 합치는 그래프를 구현했다. `추가 실습`으로는 "면접 문제 생성"(Orchestrator가 평가 역량을 판단하고, Worker가 역량별 질문을 만드는 구조)도 같은 패턴으로 확장해볼 수 있다는 메모가 남아 있었다 — Orchestrator-Worker 패턴은 "작업 개수를 LLM이 정한다"는 조건만 맞으면 도메인을 가리지 않고 재사용할 수 있는 틀이라는 걸 보여주는 예다.
