# LangGraph Human-in-the-Loop — interrupt()로 사람 승인 끼워넣기

## 언제 사람이 개입해야 하는가

- 결제, 삭제, 이메일 발송처럼 **되돌리기 어려운 작업**의 승인
- LLM이 생성한 답변·문서의 검토와 수정
- 작업에 필요한 정보가 부족할 때 추가 입력 요청

```
AI 작업 수행 → 사람의 판단이 필요한 지점에서 중단 → 검토·입력 → 작업 재개
```

LangGraph는 이 "중단하고 기다렸다가 재개"를 그래프 실행 자체를 멈추고 다시 살리는 방식으로 구현한다.

## interrupt() — 노드/Tool 내부에서 실행을 멈추는 함수

`interrupt(value)`는 노드나 Tool 함수 내부에서 호출한다. 실행이 이 코드에 도달하면 **그래프 전체가 중단**되고 `value`가 호출자에게 반환된다. 이때 Checkpointer가 당시의 그래프 state와 "여기서 멈췄다"는 사실을 기록해둔다. 나중에 같은 `thread_id`로 결정을 전달하면, **해당 노드/Tool을 처음부터 다시 실행**하는데 이번엔 `interrupt()`가 멈추는 대신 전달받은 결정값을 반환하고 다음 코드로 넘어간다.

여기서 [LangGraph 메모리와 상태](LangGraph_메모리와상태.md)에서 다룬 Checkpointer(단기 메모리, thread_id 기반)가 그대로 재사용된다는 게 흥미로웠다 — HITL은 완전히 새로운 인프라가 아니라 Checkpointer 위에 "중단점"이라는 개념 하나를 얹은 것.

## 중단에 관여하는 세 가지 값

| 구분 | 역할 |
|------|------|
| 그래프 state | 노드들이 읽고 수정하는 내부 실행 상태 |
| interrupt payload | 호출자가 검토할 질문, Tool 이름과 인자 (`interrupt(value)`의 `value`가 `__interrupt__`로 전달됨) |
| resume value | 승인자가 그래프에 돌려주는 결정 |

payload와 resume 값은 **Checkpointer가 저장할 수 있는 형태**(문자열·숫자·리스트·딕셔너리 같은 JSON 직렬화 가능 값)여야 한다는 제약이 있다.

```
첫 번째 요청: graph.invoke(작업, config)
             → Tool 내부 interrupt()에서 중단
             → payload 반환 및 그래프 실행 정보 기록

두 번째 요청: graph.invoke(Command(resume=결정), 같은 config)
             → 같은 thread_id의 상태 복원
             → 결정이 interrupt()의 반환값이 되어 실행 재개
```

**함정 포인트**: 재개할 때 `ToolNode`와 Tool 함수는 **처음부터 다시 실행**된다. 다만 `interrupt()` 호출 지점에서는 다시 멈추지 않고 전달받은 resume 값을 즉시 반환한다는 점이 핵심이다. 즉 Tool 함수 안에서 `interrupt()` 이전에 부작용(예: 로그 기록, 외부 호출)이 있다면 재개 시 그 부작용도 다시 실행된다는 뜻이므로, interrupt 이전 코드는 **재실행돼도 안전한 코드**로 짜야 한다.

거절 처리도 같은 메커니즘이다 — 새로 시작한 실행을 중단한 뒤 `resume` 값에 `{"decision": "reject", "reason": "..."}` 같은 걸 담아 전달하면, Tool이 결제를 수행하지 않고 취소 결과를 반환하도록 Tool 내부에서 resume 값을 분기하면 된다.

## 서버-클라이언트 관점: 요청 하나를 계속 붙들고 있지 않는다

실제 서비스에서는 서버가 사용자의 승인이 날 때까지 HTTP 요청 하나를 계속 열어두지 않는다. **두 번의 독립적인 API 요청**으로 나뉜다.

```
Client                              Server / Graph
  │  POST /chat  { message }
  ├──────────────────────────────────▶
  │                                   Graph 실행 → interrupt() → 중단
  │  response { thread_id, interrupt: { question } }
  ◀───────────────────────────────────┤
  │  (thread_id 저장, 사용자에게 승인 UI 표시)
  │
  │  POST /resume { thread_id, action: "approve" | "reject" }
  ├──────────────────────────────────▶
  │                                   thread_id로 중단된 Graph 식별
  │                                   → Command(resume=...) → 실행 재개 → 완료
  │  response "처리가 완료되었습니다."
  ◀───────────────────────────────────┤
```

첫 번째 요청은 "중단된 지점과 thread_id"만 응답하고 바로 끝난다. 두 번째 요청이 같은 `thread_id` + `Command(resume=...)`로 저장된 실행을 찾아서 재개한다. 실습에서는 이걸 `post_chat()`/`post_resume()`이라는 두 함수로 노트북 안에서 흉내 내서, Client가 Server 내부의 LangGraph 코드를 몰라도 endpoint 함수만 호출하면 되는 구조로 분리해봤다.

## 실습

- **게시글 발행 승인**: `publish_post(title, content)` Tool을 만들고, 발행 전에 사용자 승인을 받는 흐름(승인/거절 각각 실행해서 결과 확인).
- **실행 계획 검토(Plan-and-Execute + HITL)**: Planner가 계획을 세우면 바로 실행하지 않고 사람이 검토 — 승인하면 Executor 실행, 거절하면 추가 의견을 Planner에 돌려줘서 계획을 다시 짜고 다시 검토받는다. [LangGraph Plan-and-Execute](LangGraph_PlanAndExecute.md)의 Replanner 자리에 "사람의 승인"이 들어간 변형인 셈이다.
- **부족한 정보 질문하기**: 사용자 요청에 정보가 부족하면 LLM이 객관식 선택지가 있는 질문을 만들고, 사용자가 답변(선택 또는 직접 입력)하면 원래 요청 대신 답변을 정리하는 흐름 — HITL이 승인/거절뿐 아니라 "필요한 입력을 받아오는 용도"로도 쓰인다는 걸 보여주는 예다.
