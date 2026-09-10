# LangGraph RAG Agent — Retriever를 Tool로 등록하기

## 기본 RAG 파이프라인과 RAG Agent의 차이

기본 RAG 파이프라인은 질문이 들어올 때마다 무조건 검색을 수행한다. RAG Agent는 ReAct Agent에 Retriever를 Tool로 등록해서, **검색이 필요한지 아닌지를 LLM이 스스로 판단**하게 만든다.

| 구분 | 기본 RAG 파이프라인 | RAG Agent |
|------|----------|-----------|
| 검색 판단 | 항상 검색 | LLM이 필요 여부 판단 |
| 대화 기억 | 별도 구현 필요 | Checkpointer로 유지 |
| 검색 도구 | Retriever를 직접 호출 | Retriever를 Tool로 호출 |

실제로 "연차 휴가는 며칠인가요?"처럼 문서가 필요한 질문에는 `search_company_rules` Tool을 호출하고, "이거 영어로 번역해줘"처럼 검색이 필요 없는 질문에는 Tool 호출 없이 바로 답한다 — 같은 Agent 안에서 질문에 따라 동작이 갈린다.

## create_retriever_tool이 대신해주는 일

`create_retriever_tool(retriever, name, description, ...)`은 Retriever를 Agent가 호출 가능한 Tool로 바꿔준다.

- `retriever.invoke(query)`를 호출하는 함수를 만든다
- 검색된 `Document`들의 `page_content`를 합쳐 문자열로 반환한다
- `name`/`description`으로 LLM이 "언제 이 Tool을 써야 하는지" 판단하게 한다
- `document_prompt`로 검색 문서 하나하나의 출력 형식을 정한다
- `document_separator`로 여러 문서 사이 경계를 표시한다(예: `---`)

**함정**: 기본 설정에서는 metadata가 결과에 포함되지 않는다. 출처(source)처럼 Agent가 답변에 인용해야 하는 정보는 `document_prompt`에 `{source}`처럼 명시적으로 넣어야 한다. 이때 `document_prompt`에 쓴 metadata 키가 검색된 **모든** 문서에 존재하지 않으면 변환 과정에서 오류가 난다 — 청크마다 metadata 스키마가 다르면 여기서 터진다는 뜻이다.

Agent가 Tool을 실제로 쓰기 전에 Retriever Tool을 직접 호출해서 입력 형식과 반환 텍스트를 눈으로 확인하는 게 디버깅에 유용하다.

## 문서 기반 답변만 허용하기 (개방형 vs 제한형)

RAG Agent는 검색 결과가 없어도 LLM의 일반 지식으로 답할 수 있다. 하지만 사내 문서 QA나 고객 응대처럼 **승인된 문서 근거만 허용**해야 하는 경우가 많다. 이건 System Prompt 하나로 제어한다.

- **개방형**: System Prompt 없이. 문서 + 일반 지식으로 폭넓게 답변
- **제한형**: System Prompt로 "문서에 없으면 찾을 수 없다고 답하라"를 강제. 정확성이 중요한 경우

같은 Agent 구조에서 System Prompt만 바꿔서 두 가지 운영 모드를 만들 수 있다는 점이 인상적이었다 — Retriever Tool이나 그래프 구조를 바꾸는 게 아니라 프롬프트 레이어에서 정책을 강제하는 방식.

## 대화형 RAG — Checkpointer 결합

Checkpointer를 연결하면 "재택근무 가능 횟수는?" → (검색 후 답변) → "가장 중요한 것 하나만" → (Tool 호출 없이 이전 답변 맥락에서 선별) → "영어로 번역해줘" → (역시 Tool 호출 없이 맥락으로 처리) 같은 후속 질문 흐름이 가능해진다. Checkpointer가 없으면 "가장 중요한 것"이 뭘 가리키는지 Agent가 알 방법이 없다 — [LangGraph 메모리와 상태](LangGraph_메모리와상태.md)에서 정리한 thread_id 기반 State 유지가 여기서 그대로 쓰인다.

## 실습: SPRi AI Brief 다개월치로 대화형 RAG Agent 구성

PDF(SPRi AI Brief 9월호~11월호)를 청크로 분할 → 벡터 DB에 저장 → Retriever Tool로 변환 → `create_agent()`에 등록 → Checkpointer로 대화형으로 만드는 전체 파이프라인을 직접 구성하는 실습이었다. [LangGraph 기초](LangGraph_기초.md)의 State/Reducer, [LangGraph ReAct 에이전트](LangGraph_ReAct에이전트.md)의 Tool 설계, 이 문서의 Retriever Tool화가 한 번에 합쳐지는 실습이라 지금까지 배운 걸 조합해보는 느낌이었다.
