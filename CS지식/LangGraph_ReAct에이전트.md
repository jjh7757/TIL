# LangGraph ReAct 에이전트 — ToolNode·tools_condition과 create_agent

## ReAct = Function Calling을 그래프 안에서 반복하기

ReAct는 **Reasoning + Acting**의 줄임말이다. 기반 기술은 Function Calling(Tool Use) — LLM이 텍스트 대신 "이 함수를 이 인자로 호출해줘"라는 `tool_calls`를 반환하면, 시스템이 그 함수를 실행하고 결과를 다시 LLM에게 돌려준다. ReAct는 이 Function Calling을 **그래프 안에서 반복**하는 패턴이다.

```
Think   → LLM이 이전 메시지를 바탕으로 다음 행동을 결정
Act     → tool_calls 생성 → 시스템이 Tool을 실행
Observe → Tool 결과가 LLM에게 전달
(반복)
Answer  → tool_calls가 없으면 최종 답변
```

핵심은 **LLM이 다음 행동을 결정**한다는 것 — 어떤 Tool을 호출할지, 몇 번 반복할지, 언제 멈출지 전부 모델이 정하고 애플리케이션은 `tool_calls`를 보고 실행만 대신해준다.

## ToolNode와 tools_condition — 반복 처리를 직접 안 짜도 되는 이유

수동으로 짜면 이렇게 된다.

```python
for tool_call in response.tool_calls:
    tool_fn = tool_map[tool_call["name"]]
    result = tool_fn.invoke(tool_call["args"])
    messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
```

LangGraph는 이 반복 처리를 두 가지 내장 요소로 대신해준다.

- **`ToolNode`**: AI 메시지의 `tool_calls`를 파싱 → 해당 함수 실행 → 결과를 `ToolMessage`로 감싸 State에 추가하는 걸 자동으로 처리하는 노드.
- **`tools_condition`**: 마지막 메시지에 `tool_calls`가 있으면 `"tools"`, 없으면 `END`를 반환하는 조건 함수. 직접 짠다면 아래와 동일하다.

```python
def should_continue(state: MessagesState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END
```

`add_conditional_edges`에 매핑 dict를 넘길 수도 있지만, 라우팅 함수의 반환값이 이미 노드 이름/`END`와 같다면 생략해도 된다.

```python
graph_builder.add_conditional_edges("chatbot", tools_condition)  # 매핑 생략 가능
```

State는 `messages: Annotated[list, add_messages]` 하나만 가진 `MessagesState`로 충분한 경우가 대부분이다 — Human/AI/Tool 메시지가 전부 이 하나의 리스트에 누적된다.

## Tool은 함수가 아니라 스키마로 노출된다

Tool을 실행하는 건 시스템이지만, **LLM이 보는 건 Tool 이름·docstring·파라미터 타입으로 만든 스키마**뿐이다. 함수 내부 로직이 아무리 정확해도 docstring이 용도와 입력 형식을 구체적으로 설명하지 않으면 LLM이 언제/어떻게 써야 할지 판단하지 못한다. `@tool(parse_docstring=True)`를 쓰면 docstring의 Args 섹션까지 파싱해서 파라미터 설명으로 넘겨준다.

## create_agent — 그래프를 직접 안 짜도 되는 고수준 API

`StateGraph` + `ToolNode` + `tools_condition`을 직접 조립하는 저수준 방식과 달리, `langchain.agents.create_agent(llm, tools)`는 이 조립을 대신 해주는 고수준 API다. 실습에서는 상품 검색 Agent(`search_products`, `get_product`)를 저수준·고수준 두 가지로 각각 만들어서 비교했다 — 내부 동작(Think→Act→Observe 반복)은 같고, 그래프를 눈에 보이게 직접 제어할지 아니면 통째로 맡길지의 차이다.

## 실습: Local File Agent

파일 검색·읽기·쓰기 Tool 3종(`search_files_impl`, `read_file_impl`, `write_file_impl`)을 만들어 실제 파일시스템에 접근하는 Agent를 구성했다. 안전장치로 **작업 폴더(WORKSPACE)와 `.txt` 확장자로 접근 범위를 제한**해서, Agent가 임의 경로나 임의 파일 형식에 손대지 못하게 막았다 — Tool을 설계할 때 "무엇을 할 수 있는가"뿐 아니라 "무엇을 못 하게 막을 것인가"도 스키마/구현 레벨에서 같이 정해야 한다는 걸 보여주는 예제였다.

테스트 질문은 "ReAct 관련 파일을 찾아 읽고, 핵심 내용을 summary.txt로 저장해줘"처럼 **검색 → 읽기 → 쓰기 세 Tool을 순서대로 스스로 호출**해야 완수되는 다단계 지시였다. Agent가 이 순서를 스스로 판단해서 완주하는지 확인하는 게 실습의 핵심이었다.
