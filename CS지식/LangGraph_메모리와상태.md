# LangGraph 메모리와 상태 — Checkpointer vs Store

## 두 종류의 메모리

| 구분 | Checkpointer | Store |
|---|---|---|
| 저장 단위 | `thread_id` | namespace, key |
| 용도 | 같은 대화 이어가기 | 다른 대화에서도 사용자 정보 유지하기 |

- **Checkpointer(단기 메모리)**: 그래프가 실행될 때마다 State 스냅샷을 저장하고, 같은 `thread_id`로 다시 호출하면 저장된 State부터 이어서 실행한다. 이번 실습에서는 인메모리 구현체인 `MemorySaver`를 썼지만, SQLite/PostgreSQL 등 다른 Saver로 바꿔도 `thread_id` 기반 구조 자체는 동일하다.
- **Store(장기 메모리)**: `thread_id`(=대화 하나)를 넘어서 유지되어야 하는 정보를 저장한다. namespace로 데이터를 묶고 key로 그 안의 항목을 구분한다.
  - `put(namespace, key, value)` / `get(namespace, key)` / `search(namespace)` 세 메서드가 기본.

| 저장할 정보 | 저장 위치 | 예시 |
|---|---|---|
| 지금 대화의 흐름에 필요한 것 | State / Checkpointer | 메시지 기록, 진행 작업 단계, 도구 실행 결과 |
| 다른 대화에서도 필요한 것 | Store | 사용자 프로필, 선호 사항, 과거 요약, 결정 사항 |
| 여러 사용자가 함께 사용하는 것 | Store | 정책 값, 애플리케이션 설정 |

## 노드에서 config/store 받기

LangGraph는 노드 함수의 매개변수 이름을 보고 필요한 걸 자동으로 주입해준다.

- `state: MessagesState` — 지금 실행에서 메시지를 담은 State
- `config: RunnableConfig` — 호출 시 넘겨준 설정값, 여기서 `configurable`의 `user_id`를 읽는다
- `store: BaseStore` — `compile(store=store)`로 등록한 Store를 그대로 받는다

`thread_id`가 달라져도 Checkpointer는 대화 State를 공유하지 않지만, 같은 `user_id`로 Store에 접근하면 어떤 대화에서든 저장된 정보를 조회할 수 있다.

## namespace로 사용자별 데이터 격리

Store는 namespace + key로 데이터를 구분한다. 예를 들어 `("users", "user-001")`과 `("users", "user-002")` 각각의 `profile` key는 서로 다른 값을 가리킨다. namespace 자체를 클라이언트가 보낸 값으로 결정하면 다른 사용자 데이터에 접근할 수 있는 구멍이 생기므로, **실제 서비스에서는 클라이언트가 보낸 user_id를 그대로 신뢰하지 말고 인증된 사용자 식별자로 namespace를 강제**해야 한다는 주의점이 실습 노트에 명시돼 있었다.

## 착각하기 쉬운 것: "invoke 한 번 = 상호작용 한 번"이 아니다

1. 하나의 `graph.invoke()` 안에서도 ReAct 에이전트라면 Human → AI → Tool → AI처럼 **여러 메시지가 이미 오간다** — 전부 한 번의 실행(super-step들의 묶음) 안에서 벌어지는 일이라 착각하기 쉽다.
2. 같은 그래프를 다시 `invoke()`하면 원래는 새 실행으로 취급된다. Checkpointer를 쓰면 **여러 번의 invoke에 걸쳐서도** 대화를 이어갈 수 있다.
3. 대화 구분은 `thread_id` 단위다.
4. Store를 쓰면 특정 스레드를 넘어서까지 정보를 유지할 수 있다.

`get_state(config)`로 특정 `thread_id`의 최신 State를(`state.values`), `get_state_history(config)`로 과거 스냅샷 전체(최신순 iterator)를 확인할 수 있다.

## 대화 요약(Summarization) 패턴

대화가 길어지면 메시지가 계속 쌓여 토큰 비용이 늘어난다. 이걸 막는 표준 패턴:

```
START → chatbot → 토큰 초과? → summarize → END
                 → 토큰 이내? →            END
```

- `trim_messages`: 토큰 기준으로 최근 메시지만 남긴다.
- `RemoveMessage` + `add_messages` reducer: State의 `messages`에서 특정 메시지를 **ID 기준으로 제거**한다. `add_messages`는 `RemoveMessage`를 받으면 해당 ID의 메시지를 삭제하도록 특별 처리돼 있다.

요약 후 State 모양:

```
messages: [최근 human 메시지, 최근 ai 응답]   ← trim 후 남은 것만
summary:  "이전 대화 요약 텍스트"              ← 오래된 메시지의 압축본
```

**주의할 점**: `RemoveMessage`로 지워지는 건 그래프가 현재 들고 있는 State뿐이다. Checkpointer 저장소(과거 체크포인트)에는 원본 메시지가 그대로 남아있으므로, "완전 삭제"가 아니라 "현재 State에서만 제거"라고 이해해야 한다. 대화 자체를 영구 보존해야 한다면 별도의 로그/DB에 저장하고, LangGraph State는 최신 메시지 위주로만 유지하는 게 맞는 역할 분담이다.

## 개인 실습 메모: remember_info Tool

"기억해줘"라고 말하면 `store.put()`으로 정보를 저장하고, 이후 다른 대화에서도 `store.get()`으로 꺼내 쓰는 개인화 ReAct 에이전트 아이디어를 연습했다.

```python
@tool
def remember_info(text):
    """사용자가 기억하라고 하면 해당 text를 받아다가 store에 저장하는 함수."""
    store.put(namespace=(users, user_id), key="info", value={data: text})
```

이 방향을 더 끌고 가면, 앞서 정리한 [LangGraph ReAct 에이전트](LangGraph_ReAct에이전트.md)의 Tool 설계 원칙(스키마는 docstring으로 결정)과 이 문서의 namespace 격리 원칙을 합쳐서 "사용자별로 안전하게 기억하는 Agent"를 만들 수 있다.
