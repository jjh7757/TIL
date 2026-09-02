# LangChain 기초

LLM API를 직접 호출해도 앱을 만들 수 있지만, 기능이 늘어날수록(프롬프트 재사용, 모델 교체, 메모리, Tool, RAG) 직접 구현할 게 많아진다. LangChain은 이런 것들을 **통일된 인터페이스**로 다루게 해주는 프레임워크다.

## LangChain 생태계

하나의 라이브러리가 아니라 여러 패키지로 나뉜다.

| 패키지 | 역할 |
|---|---|
| `langchain-core` | 기본 인터페이스, LCEL, 메시지 타입 |
| `langchain` | 체인 구성, 메모리, 에이전트 등 고수준 기능 |
| `langchain-google-genai` | `ChatGoogleGenerativeAI` 등 Google 연동 |
| `langchain-community` | 서드파티 Tool, 벡터 DB 등 커뮤니티 통합 |
| `langgraph` | 상태 기반 Agent 프레임워크 |

| 기능 | 직접 구현 | LangChain |
|---|---|---|
| 프롬프트 템플릿 | 문자열 포맷팅 직접 관리 | `ChatPromptTemplate` |
| 모델 교체 | API별 코드 재작성 | 모델 이름만 변경 |
| 대화 메모리 | 히스토리 리스트 직접 관리 | `RunnableWithMessageHistory` |
| 체인 연결 | 함수 호출 순서 직접 관리 | `\|` 파이프라인 |

## ChatModel과 메시지

LangChain에서 LLM을 다루는 객체가 `ChatModel`이다. 메시지 리스트를 받아 응답 메시지를 반환한다.

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash")

messages = [
    SystemMessage(content="너는 Python 전문가야."),
    HumanMessage(content="리스트 컴프리헨션이 뭐야?"),
]
response = llm.invoke(messages)
```

| 메시지 타입 | 역할 |
|---|---|
| `SystemMessage` | LLM의 역할과 행동 설정 |
| `HumanMessage` | 사용자 입력 |
| `AIMessage` | LLM의 응답 |

`llm.invoke()`의 반환값은 문자열이 아니라 **`AIMessage` 객체**다.

| 속성 | 설명 |
|---|---|
| `response.content` | 실제 답변 텍스트 |
| `response.usage_metadata` | 입력·출력·전체 토큰 사용량 |
| `response.tool_calls` | 모델이 요청한 도구 호출 목록 |

같은 `llm` 변수에 다른 모델(`ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")`)을 할당해도 `invoke()` 호출 방식은 그대로다 — 이게 "모델 교체가 한 줄"이라는 말의 실체다.

## `invoke()`와 Runnable

LangChain의 모든 구성 요소(프롬프트, 모델, 파서, 체인)는 **Runnable**이라는 공통 인터페이스를 구현한다. `invoke()`는 이 인터페이스의 기본 실행 메서드다. `prompt.invoke()`, `llm.invoke()`, `chain.invoke()` 모두 같은 패턴이다 — **LangChain에서 뭔가를 실행할 땐 `invoke()`**라고 기억하면 된다.

## PromptTemplate과 ChatPromptTemplate

프롬프트 안의 변하는 값을 변수로 분리해두면 같은 구조를 여러 입력에 재사용할 수 있다.

```python
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate

# 역할 구분이 필요 없는 단일 문자열 프롬프트 — StringPromptValue 반환
prompt = PromptTemplate.from_template(
    "너는 {role} 전문가야. 다음 질문에 한국어로 답해줘.\n\n질문: {question}"
)

# system/human 역할을 구분하는 채팅 프롬프트 — ChatPromptValue 반환
prompt = ChatPromptTemplate.from_messages([
    ("system", "너는 {role} 전문가야. 모든 답변은 한국어로 해줘."),
    ("human", "{question}"),
])

prompt.invoke({"role": "Python", "question": "데코레이터가 뭐야?"})
```

| 구분 | f-string | `PromptTemplate` |
|---|---|---|
| 결과 | 일반 문자열 | LangChain이 처리하는 `PromptValue` |
| 재사용 | 문자열 생성 코드를 다시 실행 | 템플릿 객체를 여러 체인에서 재사용 |
| 체인 연결 | 별도 함수 작성 | `prompt \| llm \| parser`로 연결 |

f-string은 짧은 일회성 프롬프트에 적합하고, 여러 체인에서 재사용하거나 역할을 구분해야 하면 템플릿을 쓴다.

## OutputParser — `AIMessage`에서 필요한 값 꺼내기

`llm.invoke()`의 결과는 `AIMessage` 객체이므로, 텍스트만 필요하면 파서로 꺼낸다.

```python
from langchain_core.output_parsers import StrOutputParser

parser = StrOutputParser()
result = parser.invoke(response)   # response.content와 같은 문자열
```

(다른 파서 종류와 구조화 출력은 [LangChain 구조화 출력](LangChain_구조화출력.md) 참고)

## LCEL — `|`로 파이프라인 만들기

`|` 연산자로 프롬프트·모델·파서를 연결해 체인을 만든다. 데이터는 왼쪽에서 오른쪽으로 흐른다.

```python
chain = prompt | llm | parser

result = chain.invoke({"role": "Python", "question": "리스트와 튜플의 차이가 뭐야?"})
```

풀어쓰면 다음과 같다 — `chain.invoke(x)`는 `parser.invoke(llm.invoke(prompt.invoke(x)))`와 같다.

```python
result1 = prompt.invoke({...})
result2 = llm.invoke(result1)
result3 = parser.invoke(result2)
```

서로 다른 종류의 객체(프롬프트, 모델, 파서)를 `|`로 이을 수 있는 이유는 전부 Runnable이기 때문이다. 단, **앞 단계의 출력 타입이 다음 단계가 기대하는 입력 타입과 맞아야** 연결할 수 있다.

## `RunnableLambda` — 평범한 함수를 체인에 끼워 넣기

```python
from langchain_core.runnables import RunnableLambda

def to_upper_text(text: str) -> str:
    return text.upper()

to_upper = RunnableLambda(to_upper_text)
add_label = RunnableLambda(lambda text: f"결과: {text}")

text_chain = to_upper | add_label
text_chain.invoke("hello langchain")   # "결과: HELLO LANGCHAIN"
```

두 체인을 이어 붙이고 싶은데 `chain1`의 출력 타입(`str`)과 `chain2`의 입력 타입(`{"text": ...}` 딕셔너리)이 다르면 바로 연결할 수 없다. 이때 `RunnableLambda`를 **타입 변환 어댑터**로 중간에 끼운다.

```python
combined_chain = chain1 | RunnableLambda(lambda x: {"text": x, "target": "초등학생"}) | chain2
```

## `RunnablePassthrough` — 입력을 유지하며 값 추가하기

호출자는 `{"question": "..."}`만 넘기고, 체인 내부에서 검색·DB·API로 가져온 데이터를 자동으로 붙이고 싶을 때 쓴다.

```python
from langchain_core.runnables import RunnablePassthrough

def retrieve_context(question):
    return knowledge_base.get(question, "")

add_context = RunnablePassthrough.assign(
    context=lambda inputs: retrieve_context(inputs["question"])
)

chain = add_context | prompt | llm | parser
chain.invoke({"question": "Python은 누가 만들었어?"})
# 체인 내부에서 {"question": "...", "context": "검색된 문서 내용..."}로 확장된 뒤 prompt에 전달됨
```

이렇게 하면 체인의 **외부 인터페이스는 단순하게 유지**되고, 검색·context 구성 같은 세부 로직은 체인 안으로 숨길 수 있다. 이 패턴은 RAG 체인에서 자주 쓰인다.

## 참고

- [LangChain 구조화 출력](LangChain_구조화출력.md)
- [LangChain 실행과 안정성](LangChain_실행과안정성.md) — 토큰 모니터링, 에러 처리, 캐싱, batch/stream
- [LangSmith 기초](LangSmith_기초.md)
- [LangChain 메모리](LangChain_메모리.md)
- [LangChain Tool과 기본 Agent](LangChain_Tool과Agent.md)
- [RAG 기초](RAG_기초.md), [벡터 DB](벡터DB.md)
- [프롬프트 엔지니어링](프롬프트엔지니어링.md)
