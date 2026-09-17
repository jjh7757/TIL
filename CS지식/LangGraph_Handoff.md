# LangGraph Handoff — Agent가 담당권을 통째로 넘기기

## Handoff란

Handoff는 현재 Agent가 다른 Agent에게 대화의 제어권을 넘기는 방식이다. 작업 결과가 중앙 Agent로 돌아가는 [Supervisor](LangGraph_Supervisor.md)와 달리, 전환된 Agent가 새로운 담당자가 되어 사용자 요청에 응답하고 **이후 대화까지 이어간다**.

## Command로 State 변경과 이동을 함께 결정하기

`Command`는 그래프 실행을 제어하는 객체다. [Human-in-the-Loop](LangGraph_HumanInTheLoop.md)에서는 중단된 그래프에 값을 넘기려고 `resume`을 썼는데, 여기서는 노드가 State 변경과 다음 실행 위치를 동시에 정하기 위해 `update`와 `goto`를 쓴다.

일반 노드는 딕셔너리를 반환해 State만 바꾸고 다음 노드는 Edge가 정한다. `Command`를 쓰면 노드가 State 변경과 다음 실행 위치를 함께 결정할 수 있다.

```python
def classify_query(state: RoutingState) -> Command[Literal["sales", "support"]]:
    if "오류" in state["query"] or "고장" in state["query"]:
        return Command(update={"category": "support"}, goto="support")
    return Command(update={"category": "sales"}, goto="sales")
```

- `update`: 현재 State에 반영할 값
- `goto`: 다음에 실행할 노드 이름

`classify`에서 `sales`/`support`로 가는 Edge를 따로 등록하지 않아도, 실행 중 반환되는 `Command.goto`가 다음 노드를 결정한다. `Command[Literal["sales", "support"]]`의 `Literal`은 가능한 이동 대상을 명시해서, 정적 Edge가 없어도 시각화 도구가 동적 이동 후보를 그래프에 표시할 수 있게 해준다. 생략해도 실행은 되지만 시각화에서는 목적지를 미리 알 수 없다.

| 상황 | 사용 방식 |
|------|-----------|
| 다음 단계가 항상 동일 | `add_edge()` |
| 작업과 Routing 판단을 분리 | `add_conditional_edges()` |
| State 변경과 이동이 하나의 제어 동작 | `Command(update=..., goto=...)` |

고정된 흐름과 일반적인 Routing은 Edge로 분리하는 편이 구조 파악과 노드 재사용에 유리하다. State 변경과 이동이 한 덩어리의 결정일 때만 `Command`를 쓴다.

## Handoff Tool

다른 Agent로 제어권을 넘기기 위해 호출하는 Tool을 **Handoff Tool**이라 한다. 일반 Tool은 실행 결과를 반환하지만, Handoff Tool은 `Command`를 반환해 담당 Agent를 바꾸고 다른 Agent 노드로 이동시킨다.

```python
@tool
def transfer_to_support(runtime: ToolRuntime) -> Command:
    """설치, 오류, 고장 등 기술 문의를 Support Agent에게 넘긴다."""
    last_ai_message = find_last_ai_message(runtime.state["messages"])
    transfer_message = ToolMessage(
        content="Support Agent로 전환했습니다.",
        tool_call_id=runtime.tool_call_id,
    )
    return Command(
        goto="support_agent",
        update={"active_agent": "support_agent", "messages": [last_ai_message, transfer_message]},
        graph=Command.PARENT,
    )
```

- `graph=Command.PARENT`: 현재 Agent 내부 그래프가 아니라, 여러 Agent를 포함하는 **부모 그래프**의 노드로 이동하도록 지정한다.
- `ToolRuntime`: Tool 실행 시 LangChain이 자동으로 주입하는 실행 정보이며, 모델이 생성하는 Tool 인자가 아니다. `runtime.state`로 현재 메시지를 조회하고, `runtime.tool_call_id`로 Tool 호출과 실행 결과를 연결한다.

모델이 Handoff Tool을 호출하면 그 `AIMessage`는 현재 Agent의 내부 State에 자동으로 추가된다. 하지만 `Command.PARENT`로 내부 그래프를 벗어나면 이 메시지가 부모 그래프의 State에 자동 전달되지 않는다. 그래서 내부 State에서 마지막 `AIMessage`를 직접 꺼내, Tool 호출을 완료 처리하는 `ToolMessage`와 함께 `Command.update`로 부모 State에 전달해야 한다. 두 메시지를 짝짓기 위해 `ToolMessage.tool_call_id`에는 `runtime.tool_call_id`를 그대로 쓴다.

## Agent와 부모 그래프 구성

각 Agent에는 **상대 Agent로 전환하는 Handoff Tool만** 제공한다. 자신의 담당 범위면 직접 답하고, 범위를 벗어나면 Handoff Tool만 호출하도록 system prompt에서 강제한다("Handoff Tool은 한 번에 하나만 호출해").

```python
class MultiAgentState(MessagesState):
    active_agent: str

def route_to_active_agent(state: MultiAgentState) -> Literal["sales_agent", "support_agent"]:
    return state["active_agent"]

def route_after_agent(state: MultiAgentState) -> Literal["sales_agent", "support_agent", "__end__"]:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and not last_message.tool_calls:
        return "__end__"
    return state["active_agent"]

handoff_builder.add_conditional_edges(START, route_to_active_agent, ["sales_agent", "support_agent"])
handoff_builder.add_conditional_edges("sales_agent", route_after_agent, ["sales_agent", "support_agent", END])
handoff_builder.add_conditional_edges("support_agent", route_after_agent, ["sales_agent", "support_agent", END])

handoff_graph = handoff_builder.compile(checkpointer=InMemorySaver())
```

- `route_to_active_agent`: 요청 내용을 분류하지 않고 State에 저장된 `active_agent`를 그대로 선택한다 — 분류는 처음 한 번(또는 Handoff 시점)만 일어나고, 그 뒤로는 "누가 담당인지"만 보고 라우팅한다.
- `route_after_agent`: Agent가 Handoff 없이(Tool 호출 없이) 답변을 마치면 그래프를 종료하고, Handoff Tool을 호출했다면 바뀐 `active_agent`로 다시 라우팅한다.

## 실행 결과: 담당이 유지된다는 것의 의미

같은 `thread_id`를 쓰면 Handoff 이후에도 현재 담당 Agent가 State(`active_agent`)에 남아 있다. 첫 요청("가격 알려줘")은 `sales_agent`가 처리하고, 이어서 기술 문의("Wi-Fi 연결 안 됨")를 보내면 `transfer_to_support`가 호출되어 `active_agent`가 `support_agent`로 바뀐다. **여기서 중요한 건, 다음 후속 질문("재부팅했는데도 안 돼")에서 `active_agent`를 다시 지정하지 않아도 `support_agent`부터 실행된다는 점**이다 — Handoff가 다시 일어나기 전까지는 한번 넘어간 담당 Agent가 계속 대화를 맡는다. 이후 "다른 색상과 가격도 알려줘"처럼 판매 문의로 돌아가면 `transfer_to_sales`가 다시 호출되어 담당이 바뀐다.

## 언제 사용할까

| 패턴 | 주요 역할 | 예시 |
| --- | --- | --- |
| Router | 요청을 받아 적절한 Agent에게 분배한다. | 문의를 분류해 판매 또는 기술 지원 Agent로 전달 |
| Supervisor | 작업을 위임하고, 중간 결과를 보며 다음 작업을 결정한다. | 조사 결과로 보고서를 작성하게 하고, 검토 결과에 따라 수정을 요청 |
| Handoff | 현재 Agent가 다른 Agent에게 담당권을 넘기고, 전환된 Agent가 대화를 이어간다. | 판매 상담 중 기술 지원으로 전환한 뒤 후속 질문도 Support Agent가 처리 |

Router는 요청 분류·분배 자체에 초점을 두고, 새 요청마다 다시 실행될 수 있다. Supervisor는 전문가의 결과를 받아 다음 작업이 필요한지 판단하며 위임·판단을 반복한다. Handoff는 "지금 누가 담당인가"를 State에 저장해 여러 턴에 걸쳐 유지한다는 점이 셋 중 가장 다르다. 요청 분류와 분배가 중심이면 Router, 중간 결과에 따른 조율이 중심이면 Supervisor, 여러 턴에 걸친 담당 유지·전환이 중심이면 Handoff를 고려한다.
