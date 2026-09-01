# LangChain 대화 메모리 (Chat Memory)

LLM 호출은 기본적으로 **stateless**다 — 이전 호출을 전혀 기억하지 못한다. 대화 맥락을 유지하려면 매 호출마다 이전 메시지를 함께 전달해야 한다.

```python
response1 = llm.invoke([HumanMessage(content="내 이름은 철수야")])
response2 = llm.invoke([HumanMessage(content="내 이름이 뭐였지?")])
# response2는 철수라는 이름을 모른다 — 첫 번째 호출 내용이 두 번째 요청에 전혀 없었으므로
```

## 수동으로 히스토리 전달하기

이전 메시지들을 리스트에 계속 누적해서 함께 보내면 맥락이 유지된다.

```python
messages = [
    SystemMessage(content="너는 친절한 상담사야."),
    HumanMessage(content="내 이름은 철수야"),
]
response1 = llm.invoke(messages)

messages.extend([response1, HumanMessage(content="내 이름이 뭐였지?")])
response2 = llm.invoke(messages)   # 이번엔 "철수"라고 답한다
```

## `InMemoryChatMessageHistory` — 세션별로 관리하기

메시지 추가·조회를 위한 LangChain Core의 기본 인메모리 구현. 세션 ID별로 객체를 나누면 여러 대화를 독립적으로 관리할 수 있다.

```python
from langchain_core.chat_history import InMemoryChatMessageHistory

history_store: dict[str, InMemoryChatMessageHistory] = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in history_store:
        history_store[session_id] = InMemoryChatMessageHistory()
    return history_store[session_id]

def chat(session_id: str, user_input: str) -> str:
    history = get_session_history(session_id)
    user_message = HumanMessage(content=user_input)
    response = llm.invoke([
        SystemMessage(content="너는 친절한 상담사야."),
        *history.messages,      # 이 세션의 이전 대화 전체
        user_message,
    ])
    history.add_messages([user_message, response])
    return response.content

chat("user-1", "내 이름은 철수야")
chat("user-1", "내 이름이 뭐였지?")   # "철수"
chat("user-2", "내 이름이 뭐야?")     # user-1의 기록이 섞이지 않아 모른다
```

`InMemoryChatMessageHistory`는 대화 히스토리의 기본 동작을 익히기엔 좋지만, **프로세스가 종료되면 기록이 사라진다.** 실제 서비스에서는 데이터베이스 기반 저장소나 LangGraph의 state/checkpointer로 영속적으로 관리한다.

## Context window 관리 — `trim_messages()`

대화가 길어질수록 비용·지연 시간이 늘고 context window를 넘을 수 있다. **DB에 저장하는 원본 메시지**와 **이번에 모델에 보낼 메시지**는 별개의 문제다.

| 방법 | 장점 | 단점 |
|---|---|---|
| 메시지 트리밍 | 단순, 추가 호출 비용 없음 | 오래된 맥락 유실 |
| 대화 요약 | 오래된 핵심 맥락을 압축 | 추가 호출 비용, 요약 오류 가능성 |
| 검색 기반 선택 | 관련 과거 정보만 선택 | 검색·인덱싱 설계 필요 |

`trim_messages()`는 원본 리스트나 저장된 히스토리를 **삭제하지 않고**, 조건에 맞게 선택된 새 메시지 목록만 반환한다 — 전체 대화는 보존하면서 이번 호출에 필요한 최근 대화만 모델에 전달할 수 있다.

```python
from langchain_core.messages import trim_messages

trimmer = trim_messages(
    max_tokens=80,       # 트리밍 결과에 허용할 최대 토큰 수
    strategy="last",     # 최근 메시지를 우선해서 남김
    token_counter=llm,   # 토큰 수를 계산할 모델
    include_system=True, # 첫 system 메시지는 유지
    start_on="human",    # 트리밍된 대화는 human 메시지부터 시작
)
trimmed = trimmer.invoke(long_history)
```

```
전체 히스토리 저장 → 토큰 수 계산 → 최근 메시지 선택 → 대화 시작 역할 정리 → 모델에 전달
```

트리밍된 결과에 오래된 메시지가 빠지면 모델은 그 내용을 전혀 모른다 — 중요한 사용자 정보까지 단순히 잘려나갈 수 있으므로, 실제 서비스에서는 최근 메시지 + 대화 요약(또는 검색된 과거 정보)을 함께 전달하는 방법을 고려한다.

## Short-term memory vs Long-term memory

두 메모리는 저장 기간이 아니라 기억을 쓰는 **범위(scope)**로 구분한다.

| 구분 | Short-term memory | Long-term memory |
|---|---|---|
| 범위 | 현재 대화 세션 | 여러 대화 세션 |
| 저장 내용 | 현재 대화 메시지와 작업 맥락 | 사용자 선호·프로필·기억할 사실 |
| 예 | "앞에서 내 이름을 철수라고 말했어" | "이 사용자는 Python 백엔드 개발자다" |

이 문서에서 다룬 `InMemoryChatMessageHistory`, `trim_messages()`는 모두 short-term memory에 해당한다. 세션을 넘어 정보를 저장하고 필요할 때 찾아 쓰는 long-term memory는 별도의 저장소·검색 설계가 필요하다.

## 참고

- [LangChain 기초](LangChain_기초.md)
- [비동기 기초](파이썬기초/21_비동기기초.md)
