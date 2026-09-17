# LangGraph Supervisor — Subagent를 Tool로 위임하기

## Multi-Agent란

Multi-Agent 시스템은 하나의 Agent가 모든 작업을 처리하는 대신, 서로 다른 역할을 맡은 여러 Agent가 협력해 하나의 목표를 달성하는 구조다. 각 Agent는 역할에 맞는 Prompt·Tool·Context를 독립적으로 가지며, Agent 사이의 작업 전달과 결과 공유로 복잡한 작업을 나눠 처리한다.

## Multi-Agent를 고려하는 이유

하나의 Agent가 너무 많은 역할·Tool·Context를 담당하면 지시 충돌과 Tool 선택 오류가 늘어난다. 역할별 Agent로 분리하면 각 Agent가 자신의 작업에 필요한 지시와 정보에만 집중할 수 있다.

| 이점 | 설명 |
|------|------|
| 역할과 Context 분리 | 각 Agent가 담당 작업에 필요한 정보에 집중 |
| Tool과 권한 분리 | Agent별로 필요한 Tool만 제공 |
| 독립적인 설계와 평가 | 역할마다 Prompt, 모델, 평가 기준을 다르게 설정 |
| 동적인 작업 위임 | 요청과 중간 결과에 따라 적절한 Agent를 선택 |

역할이 단순하고 실행 순서가 고정되어 있다면 단일 Agent나 일반 Workflow가 더 적합하다. Multi-Agent는 모델 호출 수·지연 시간·비용과 실패 지점을 늘리므로, 역할 분리와 동적 위임의 이점이 충분할 때만 쓴다.

## Supervisor 패턴

중앙의 Supervisor가 작업을 분석해 적절한 Subagent에 분배하고, 각 결과를 종합해 최종 응답을 만드는 구조다.

```text
사용자 → Supervisor Agent
             ├─→ Research Agent
             ├─→ Writer Agent
             └─→ Reviewer Agent
```

## 구현: Subagent를 `@tool`로 감싸기

보고서 작성 과정을 자료 조사·작성·검토로 나눴다. `create_agent`로 만든 각 Subagent를 `@tool` 함수로 감싸 Supervisor의 Tool로 등록한다. 각 Tool은 작업 설명을 Subagent에 전달하고 마지막 응답만 Supervisor에 반환한다.

```python
researcher_agent = create_agent(model=search_llm, tools=[], system_prompt="...", name="researcher")
writer_agent = create_agent(model=llm, tools=[], system_prompt="...", name="writer")
reviewer_agent = create_agent(model=llm, tools=[], system_prompt="...", name="reviewer")

@tool
def research(query: str) -> str:
    """주제에 관한 최신 자료와 출처를 조사한다."""
    result = researcher_agent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].text

# write_report, review_report도 같은 방식

supervisor_agent = create_agent(
    model=llm,
    tools=[research, write_report, review_report],
    system_prompt="너는 보고서 작성 팀의 Supervisor다. ... 중간 작업 과정은 사용자에게 설명하지 마.",
    checkpointer=InMemorySaver(),
)
```

**Checkpointer는 전체 대화를 관리하는 최상위 Supervisor에만 설정한다.** Subagent는 매번 독립적으로 `invoke`되는 일회성 호출이라 자체 대화 기록을 유지할 필요가 없다.

## Supervisor의 동작 방식

Supervisor 자체도 필요한 작업을 판단하고 Tool을 실행하고 결과를 관찰해 다음 행동을 결정하는 **ReAct 방식**으로 동작한다. 다른 점은 여기서 Tool이 독립적인 지시와 Context를 가진 Subagent를 호출한다는 것이다. 자료 조사가 필요하면 `research`를 호출하고, 반환된 결과를 바탕으로 보고서 작성이나 검토를 위임한 뒤 최종 응답을 만든다. 같은 `thread_id`로 이어지는 후속 요청("정보가 부족한 것 같은데, 추가 정보를 모아줘")에도 Supervisor가 대화 맥락을 보고 필요한 Tool을 다시 선택해서 호출한다.

## Router / Supervisor / Handoff 비교

| 패턴 | 주요 역할 | 예시 |
| --- | --- | --- |
| Router | 요청을 받아 적절한 Agent에게 분배한다. | 문의를 분류해 판매 또는 기술 지원 Agent로 전달 |
| Supervisor | 작업을 위임하고, 중간 결과를 보며 다음 작업을 결정한다. | 조사 결과로 보고서를 작성하게 하고, 검토 결과에 따라 수정을 요청 |
| Handoff | 현재 Agent가 다른 Agent에게 담당권을 넘기고, 전환된 Agent가 대화를 이어간다. | 판매 상담 중 기술 지원으로 전환한 뒤 후속 질문도 Support Agent가 처리 |

Supervisor는 항상 중앙으로 결과가 돌아온다는 점에서, 담당 자체가 다른 Agent로 넘어가 이후 대화를 그 Agent가 이어가는 [Handoff](LangGraph_Handoff.md)와 구분된다. 셋을 엄격히 구분할 필요는 없고 필요에 따라 함께 쓸 수 있다 — 요청 분류·분배가 중심이면 Router, 중간 결과에 따른 작업 조율이 중심이면 Supervisor, 여러 턴에 걸친 담당 유지·전환이 중심이면 Handoff를 고려한다.
