# LangGraph 멀티 에이전트 종합 실습 — Router로 조사·기획·검토 조합하기

## 과제

사용자 요청에 따라 조사(research)·기획(planning)·검토(review) 세 에이전트 중 필요한 것만 선택해서 실행하고, 복합 요청에서는 앞 단계 결과를 다음 단계에 넘기고, 같은 세션에서 대화 맥락을 기억하는 멀티 에이전트 시스템 만들기. 대학가 소자본 창업 기획을 검증 시나리오로 사용.

## Router vs Supervisor — 왜 Router를 선택했나

어제 정리한 [Supervisor](LangGraph_Supervisor.md)는 중앙 Agent가 Tool로 감싼 Subagent를 스스로 판단해서 호출하는 방식이다. 이번엔 그 대신 **Router(요청 분류) + 조건부 엣지**로 짰다.

- 세 에이전트 사이에 **고정된 의존 순서**가 있다 (기획은 조사 결과를 반영해야 하고, 검토는 항상 마지막) — 순서 자체를 LLM의 자율 판단에 맡길 필요가 없었다.
- Router 한 번의 구조화된 출력(`agents: list[...]`)으로 "이번 요청에 필요한 에이전트 집합"을 정하고, 그래프는 항상 `research → planning → review` 순서로 그중 선택된 것만 통과시키는 조건부 엣지 3개로 충분했다.
- Supervisor처럼 에이전트별 Tool 호출 결과를 매번 관찰하고 다음 행동을 다시 판단하는 ReAct 루프가 필요 없어서, 호출 수와 실패 지점이 줄었다.

**결론**: 실행 순서가 고정돼 있고 "무엇을 실행할지"만 동적으로 정하면 되는 경우엔 Router가 더 예측 가능하고 단순하다. 순서 자체가 상황에 따라 바뀌거나 중간 결과를 보고 다음 행동을 유연하게 정해야 하면 Supervisor가 맞는다.

## 다른 State 스키마의 서브그래프는 래퍼 노드로 연결

조사 에이전트는 [Orchestrator-Worker](LangGraph_OrchestratorWorker.md) 패턴(항목 생성 → `Send`로 동적 fan-out → 결과 종합)을 쓰는 독립 [서브그래프](LangGraph_Subgraph.md)다. 상위 그래프의 `OverallState`와 필드가 전혀 다르기 때문에, 그대로 `add_node`할 수 없고 입출력을 변환하는 래퍼 함수가 필요했다.

```python
def call_research(state: OverallState):
    result = research_app.invoke({"request": state["request"]})
    return {"research_report": result["response"]}
```

같은 이유로 `planning`/`review`도 `create_agent`가 요구하는 `{"messages": [...]}` 입력·출력 형식과 상위 그래프의 `plan`/`approved` 필드를 서로 변환하는 래퍼 노드(`call_planning`, `call_review`)로 감쌌다.

## "승인" 같은 자유 텍스트 신호는 부분 문자열로 판정하면 오탐난다

계획/검토 에이전트가 "문제 없으면 '승인'이라고 말해"라는 지시를 받는데, 실제 응답에 "인허가 **승인**", "추가 조사 후 최종 **승인** 처리하겠습니다"처럼 승인과 무관한 문맥에서도 그 단어가 섞여 나왔다. `"승인" in text`로 판정하면 **아직 승인 안 된 응답도 승인으로 오탐**한다.

해결: 프롬프트에서 "마지막 줄에 다른 말 없이 '승인'만 작성해"로 형식을 강제하고, 판정도 부분 문자열 검사가 아니라 **마지막 줄과 정확히 일치하는지**로 바꿨다.

```python
def _is_approved(text: str) -> bool:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return bool(lines) and lines[-1] == "승인"
```

자유 텍스트에서 상태를 뽑아낼 땐 "그 단어가 있는가"가 아니라 "그 단어가 정해진 위치·형식으로 있는가"를 봐야 오탐을 줄인다는 걸 실제 응답으로 확인한 사례.

## 세션 상태 재사용의 두 가지 반대 방향 함정

Checkpointer로 세션 전체 State가 누적되니까, "이전 턴에 만든 계획을 이어받아 수정"하는 기능을 넣으려고 했는데 두 번 연속으로 반대 방향의 버그를 만났다.

1. **처음**: `state.get("plan")`이 있으면 무조건 "이전 계획 수정" 모드로 들어가게 짰다 → 완전히 무관한 새 요청("이번엔 카페 창업 계획 세워줘")도 이전 턴의 낡은 계획(덮밥집)을 "이어받아 수정"하려고 해서 내용이 섞였다.
2. **고치면서**: "이번 턴에 그 에이전트가 실제로 실행됐는지"로만 판단하게 바꿨다 → 이번엔 정당한 후속 참조("이 계획 검토해줘")가 깨졌다. review만 실행되는 턴이라 이전 `plan`을 아예 안 보고, 요청 문장 자체("이 계획 검토해줘")를 검토 대상으로 삼아버렸기 때문.

**해결**: state에 값이 남아있다는 사실 자체나 이번 턴에 뭐가 실행됐는지만으로는 "이 요청이 이전 결과를 가리키는가"를 판단할 수 없었다. 결국 Router가 `agents`(무엇을 실행할지)와 별도로 `is_followup`(이 요청이 이전 계획/조사 결과를 가리키는 후속 요청인지)까지 구조화된 출력으로 같이 판단하게 했다. 코드로 추론할 수 없는 "이게 이어지는 요청인가, 새 주제인가"라는 판단은 규칙으로 흡수하려 하지 말고 LLM에게 맡겨야 하는 부분이었다.

## 같은 함정이 UI 출력에도 있었다

`main.py`의 결과 출력도 처음엔 `if result.get("research_report")`로 체크했는데, 이러면 4번째 요청에서 만든 조사 결과가 이후 요청(조사가 전혀 필요 없는 후속 수정 요청)에도 계속 다시 출력됐다. State에 값이 존재하는 것과 이번 턴에 그 값이 실제로 갱신된 것은 다르다는 같은 원칙이 노드 로직뿐 아니라 화면 출력에도 그대로 적용된다.

```python
agents_to_run = result.get("agents_to_run", [])
if "research" in agents_to_run:
    print("- 조사 결과:\n" + result["research_report"])
```

## 그래프 구조를 직접 확인하기

`app.get_graph().draw_mermaid()` / `draw_mermaid_png()`로 컴파일된 그래프의 실제 노드·엣지를 뽑아볼 수 있다. 조건부 엣지(점선)와 고정 엣지(실선)가 구분돼서, 코드로 짠 라우팅 로직이 의도한 그래프 모양과 일치하는지 눈으로 바로 검증할 수 있었다.
