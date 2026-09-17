# LangGraph Subgraph — 그래프를 노드로 재사용하기

## Subgraph란

LangGraph에서는 별도로 만든 그래프를 부모 그래프의 노드로 등록할 수 있다. 이렇게 다른 그래프에 포함된 그래프를 **Subgraph**라 한다.

- **재사용**: 미리 만든 그래프를 여러 워크플로우의 노드로 활용할 수 있다.
- **개발·관리 용이**: 복잡한 흐름을 역할별 그래프로 나누어 구현하고 테스트할 수 있다. 부모 그래프에서는 전체 작업 순서에만 집중한다.
- **State 분리**: Subgraph가 내부 작업 데이터를 별도로 관리하고, 부모와는 필요한 입력·출력만 주고받도록 구성할 수 있다.

단순한 작업은 일반 노드로도 충분하다. 여러 단계로 구성된 작업 흐름을 하나의 단위로 묶어 관리하거나 재사용할 때 Subgraph의 장점이 크다.

## 같은 State 스키마를 공유하는 경우

부모와 Subgraph의 State 스키마가 같으면, **컴파일된 그래프를 그대로 `add_node`에 전달**하면 된다.

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    research: str

research_graph = research_builder.compile()   # 이미 컴파일된 Subgraph
writing_graph = writing_builder.compile()

parent_builder = StateGraph(AgentState)
parent_builder.add_node("prepare", prepare_node)      # 일반 노드
parent_builder.add_node("researcher", research_graph)  # 컴파일된 그래프를 그대로 노드로
parent_builder.add_node("writer", writing_graph)
```

부모와 두 Subgraph가 `messages`·`research` 필드를 가진 같은 `AgentState`를 쓰면, 각 노드는 필요한 필드만 갱신하고 나머지는 그대로 유지된다 — 노드가 반환하는 값은 State 전체가 아니라 변경분이라는 원칙은 Subgraph를 노드로 쓸 때도 동일하게 적용된다.

## Subgraph 실행 과정 스트리밍

기본값인 `subgraphs=False`에서는 부모 그래프의 노드 결과만 받는다. 이때 Subgraph는 부모 그래프의 노드 하나로만 보인다. `subgraphs=True`를 지정하면 부모 그래프뿐 아니라 내부 Subgraph 노드에서 발생한 결과도 함께 받는다.

- `subgraphs=False`: `chunk`만 반환
- `subgraphs=True`: `(namespace, chunk)`를 반환. `namespace`는 이벤트가 발생한 그래프의 경로, `chunk`는 `stream_mode="updates"` 기준 `{노드 이름: 변경된 State}`

```python
for namespace, chunk in parent_graph.stream(
    {"messages": [HumanMessage(content="...")]},
    subgraphs=True,
    stream_mode="updates",
):
    ...
```

두 실행 결과를 비교하면 `subgraphs=True`일 때만 Subgraph 내부 노드(`research_start`, `research`, `write` 등)가 스트림에 추가로 찍히는 걸 확인할 수 있다.

## 부모와 Subgraph의 State가 다른 경우

State 전체 구조가 달라도, 주고받을 필드의 이름과 데이터 형식이 호환되면 컴파일된 Subgraph를 그대로 `add_node`에 전달할 수 있다. 하지만 필드 이름이나 형식이 다르면 **래퍼 함수**로 입력·출력을 변환해야 한다.

- **필드 이름이 다른 경우**: 부모의 `analysis_result`와 Subgraph의 `analysis`처럼 같은 데이터를 다른 이름으로 저장할 때
- **데이터 형식이 다른 경우**: 부모는 `messages`에 메시지 목록을 저장하지만 Subgraph는 `request`에 요청 문자열을 받을 때

```python
def analysis_wrapper(state: ParentState):
    sub_input = {"request": state["messages"][-1].text}
    sub_result = analysis_graph.invoke(sub_input)      # Subgraph는 invoke로 직접 호출
    return {"analysis_result": sub_result["analysis"]}  # 부모 State 형식으로 변환해서 반환

parent_builder.add_node("analysis", analysis_wrapper)  # 래퍼 함수를 노드로 등록
```

기존 그래프를 다른 State 구조의 부모 그래프에서 재사용할 때 이런 변환이 필요하다. 핵심은 Subgraph 자체는 손대지 않고, **부모 쪽 노드(래퍼 함수)에서만 변환을 흡수**한다는 점이다.

## 실습: 학습 콘텐츠 생성 그래프

학습 주제를 설명하고, 설명 내용을 바탕으로 확인 문제를 생성하는 그래프를 두 가지 Subgraph 결합 방식으로 구현했다.

- **설명 Subgraph**: 부모와 같은 `LearningState`(`topic`/`explanation`/`quiz`)를 그대로 쓰므로, 컴파일된 그래프를 `add_node('explanation', explanation_graph)`로 바로 등록.
- **퀴즈 Subgraph**: 별도의 `QuizState`(`source_text`/`questions`)를 쓰므로, `quiz_wrapper` 함수가 부모의 `explanation`을 Subgraph의 `source_text`로 넘기고, 반환된 `questions`를 부모의 `quiz`에 저장한 뒤 `add_node('quiz', quiz_wrapper)`로 등록.

같은 그래프 안에서 "노드가 곧 그래프 자체"인 경우와 "노드가 그래프를 감싼 함수"인 경우가 공존할 수 있다는 걸 보여주는 예다. `subgraphs=True, stream_mode="updates"`로 실행하면 `explanation`/`quiz` 두 노드 실행과 그 내부 Subgraph 단계까지 namespace별로 확인할 수 있다.
