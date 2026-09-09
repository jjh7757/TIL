# LangGraph 기초 — 분기·루프·Reducer와 재시도 그래프

## Chain으로는 안 되는 것

LCEL Chain은 `입력 → 프롬프트 → 모델 → 출력 파서 → 결과`처럼 정해진 순서로만 흐르는 직선형 파이프라인이다. 하지만 실제로는 조건 분기, 반복(검색 결과가 부족하면 재검색), 중간 상태 누적, 사람 승인 대기, 장애 후 복구, Agent의 동적 Tool 선택처럼 **제어 로직이 필요한 상황**이 자주 나온다. 이걸 일반 Python 코드(if/while)와 Chain을 조합해서 구현할 수는 있지만, 분기·반복이 늘어날수록 제어 로직이 Chain 밖으로 흩어져서 흐름을 추적하기 어려워진다. LangGraph는 이 제어 흐름과 상태 변화를 **명시적인 그래프**로 표현하게 해주는 프레임워크다.

| 필요한 제어 흐름 | LangGraph 개념 |
|---|---|
| 조건 분기 | 조건부 Edge |
| 반복과 종료 조건 | 순환 구조 + 조건부 Edge |
| 중간 결과 누적 | State, Reducer |
| 사람의 개입 | Interrupt, Checkpoint |
| 병렬 처리와 취합 | Send, Reducer |
| 장애 후 복구 | Checkpoint |
| 동적인 행동 선택 | Agent, ToolNode |

## Chain → Workflow → Agent 스펙트럼

제어 주체가 누구냐에 따라 스펙트럼으로 나뉜다.

```
개발자가 흐름 결정                                    LLM이 흐름 결정
├──────────────────────────────────────────────────────────┤
Chain       Workflow        Agent           Autonomous Agent
(직선)       (분기+루프)     (LLM이 판단)            (완전 자율)
```

Chain은 흐름이 고정(번역→요약→출력), Workflow는 개발자가 분기/루프를 설계(검색 결과 부족하면 재검색), Agent는 LLM이 다음 행동(어떤 Tool을 몇 번 쓸지)을 판단한다. **LangGraph는 이 스펙트럼 전체를 구현할 수 있는 프레임워크**라, Chain으로 시작해서 나중에 Workflow나 Agent로 확장할 때도 같은 틀을 쓸 수 있다.

## State / Node / Edge

- **State**: 그래프 전체가 공유하는 데이터. `TypedDict`로 정의한다 — 런타임에는 일반 `dict`와 동일하게 동작하지만 IDE 자동완성·타입 검사를 지원한다는 차이만 있다.
- **Node**: 처리 단계를 나타내는 Python 함수. `state`를 받아 필요한 값을 꺼내 처리하고, **업데이트할 필드만 dict로 반환**한다. 반환된 dict는 기존 State에 병합된다.
- **Edge**: 노드 간 연결. `add_edge(A, B)`는 고정 연결, `add_conditional_edges(A, routing_fn, {반환값: 노드})`는 라우팅 함수의 반환값에 따라 다음 노드가 결정된다. 라우팅 함수가 이미 노드 이름이나 `END`를 그대로 반환한다면 매핑 dict 자체를 생략할 수 있다.

노드를 나눌지 말지는 ①책임이 분리되는가 ②상태가 의미 있게 바뀌는가 ③분기·재시도가 필요한가 ④관찰(로그·소요시간·오류 확인)이 필요한가로 판단한다. 반대로 항상 같이 실행되고 개별 분기·재시도·관찰이 필요 없는 작은 작업은 한 Node 안에 몰아넣어도 된다.

`graph.invoke(state)`는 실행이 끝난 뒤 최종 State를 반환하고, `graph.stream(state)`는 기본적으로 **각 노드가 실행된 뒤의 State 업데이트**를 순서대로 반환한다(`llm.stream()`이 토큰 단위로 스트리밍하는 것과는 다른 개념). 각 단계의 전체 State를 보고 싶으면 `stream_mode="values"`를 지정한다.

## Reducer — State를 어떻게 합칠지 정하기

노드가 반환한 값은 기본적으로 기존 State 값을 **덮어쓴다**. `Annotated[타입, reducer함수]`로 필드를 선언하면 새 값을 기존 값과 어떻게 합칠지 바꿀 수 있다.

```python
name: str                               # reducer 없음 → 덮어쓰기
messages: Annotated[list, add_messages] # 메시지 형식으로 변환하며 누적
logs: Annotated[list, operator.add]     # 단순 리스트 이어붙이기(+)
```

`add_messages`는 문자열·dict 등 여러 입력 형식을 메시지 객체로 변환해가며 누적하는 메시지 전용 Reducer라 대화 기록에 주로 쓰고, 단순히 리스트를 이어 붙이기만 하면 되는 로그·결과 목록에는 `operator.add`로 충분하다.

## 실습: 글 작성 → 검토 → 재작성 루프, 그리고 정답과 내 구현의 차이

`write → review → (통과? END : write로 복귀)` 구조의 그래프를 만드는 실습에서, 정답 노트북과 내가 직접 짠 버전이 같은 문제를 다르게 풀어서 비교가 됐다.

**상태 설계**: 정답은 `sentense`(오타 그대로 필드명)와 `feedback`을 **최신 값만 덮어쓰는 일반 필드**로 뒀다. 나는 `explains`/`feedbacks`를 `Annotated[list, add_messages]`로 선언해서 **모든 시도의 이력**을 누적하고, 재작성 프롬프트에 "이전글 1 / 피드백 1 / 이전글 2 / ..." 식으로 전체 히스토리를 넣었다. 정답보다 프롬프트가 길어지는 대신, LLM이 이전에 뭘 시도했다 실패했는지까지 보고 다음 시도를 개선할 여지가 생긴다 — 트레이드오프가 있는 설계 선택이라는 걸 정답과 나란히 보고서야 알았다.

**재시도 종료 조건**: 둘 다 `attempt` 카운터를 두고 `route_by_result`에서 `attempt >= N`이면 강제로 `'pass'`를 리턴해 루프를 끊는다(정답은 3회, 나는 5회). 이 카운터를 **write 노드가 리턴하는 dict에 포함시키지 않으면** 그래프 State에 `attempt` 채널이 아예 생기지 않고, 이후 `state['attempt']`로 접근하는 순간 `KeyError`가 난다 — 실제로 처음 구현할 때 이 실수를 했다. `state.get('attempt', 0)`으로 읽는 건 안전하지만, 반환 dict에 넣는 걸 빼먹으면 다음 노드에서 죽는다는 게 함정이었다.

**분기 방식 3가지**: 정답 주석에 "1. 프롬프트로 분리 2. if문으로 node 내에서 분리 3. node 자체를 분리"라는 세 가지 옵션이 적혀 있었다. 처음 버전(cell 55)은 `attempt == 1`일 때 if문으로 조기 리턴해서 분리했지만, class로 리팩터링한 최종 버전(cell 59)에서는 이 if문을 없애고 **프롬프트 자체가 "draft와 feedback이 비어있다면 topic에 대해서 바로 써라"고 분기를 흡수**하도록 바꿨다. if문을 프롬프트로 옮기면 코드는 짧아지지만 분기 조건이 프롬프트 텍스트 안에 묻혀서 눈에 잘 안 띄는 대가가 있다.

## class로 llm 갈아끼우기 + FakeListChatModel

`WriteGraph.__init__(self, llm, llm_with_review_result)`처럼 **write용 llm과 review용 llm을 아예 별도 생성자 인자로 분리**해서 주입하는 게 정답의 핵심이었다. 이러면 "review는 항상 진짜로 판단하고 write만 가짜로 바꿔서 재시도 루프를 테스트한다"는 요구사항이 시그니처만 봐도 명확해진다.

나는 처음에 `llm` 인자 하나만 받고, `FakeLlm.with_structured_output()`이 내부에서 진짜 `real_llm.with_structured_output()`에 위임하는 방식으로 같은 효과를 냈다 — 인자는 하나지만 클래스 내부에서 "review는 항상 진짜"를 구현한 셈이다. 결과적으로 같은 결론(review는 항상 진짜 LLM으로 판단)에 서로 다른 방식(생성자 시그니처로 강제 vs 래퍼 내부 위임)으로 도달했다.

가장 크게 배운 건 `langchain_core.language_models.fake_chat_models.FakeListChatModel`의 존재였다.

```python
from langchain_core.language_models.fake_chat_models import FakeListChatModel

fake_llm = FakeListChatModel(responses=[
    "일부러 부실하게 쓴 글",   # review가 fail 하도록
    "제대로 쓴 긴 글",         # review가 pass 하도록
])
```

`invoke()`를 호출할 때마다 `responses` 리스트의 다음 항목을 순서대로 돌려주는, **랭체인이 이미 제공하는 테스트 전용 챗모델**이다. 나는 처음에 `invoke()`/`with_structured_output()`을 직접 흉내 내는 `FakeLlm` 클래스를 만들었는데, 정답은 이 내장 클래스 하나로 끝냈다. 다만 정답의 테스트는 **write까지 통째로 가짜(canned 문자열 2개)** 로 대체하고 review만 진짜로 유지하는 방식이라, 마지막 통과하는 글도 실제 LLM이 생성한 게 아니라 미리 써둔 문자열이다 — review 자체가 진짜 LLM이니 "정상 동작 확인"의 핵심은 review 쪽에 있고, write까지 진짜로 돌릴 필요는 없다는 게 정답의 관점이었다.
