# LangChain Tool과 기본 Agent

[Gemini 함수 호출](Gemini_함수호출.md)에서 본 개념(모델은 실행 권한이 없고 요청만 한다)을 LangChain으로 다루는 방법. 이름만 다를 뿐 원리는 같다 — LangChain에서는 "함수"를 **Tool**이라 부른다.

```
사용자 질문 → LLM이 판단 → Tool 호출 필요?
  → Yes: Tool 이름 + 인자 반환 → Tool 실행 → 결과를 LLM에 전달 → 최종 응답
  → No: 바로 텍스트 응답
```

## `@tool` 데코레이터 — 함수를 Tool로

Python 함수를 LangChain Tool로 바꾸는 가장 간단한 방법. **docstring이 Tool의 설명이 되고, 타입 힌트가 인자 스키마가 된다** — 이걸 보고 LLM이 언제 어떤 인자로 호출할지 판단하므로 둘 다 정확하게 써야 한다.

```python
from langchain_core.tools import tool

@tool(parse_docstring=True)
def search_weather(city: str) -> str:
    """주어진 도시의 현재 날씨를 검색한다.

    Args:
        city: 날씨를 검색할 도시 이름. 예: '서울', '부산'
    """
    weather_data = {"서울": "맑음, 22도, 습도 45%", "부산": "흐림, 19도, 습도 72%"}
    return weather_data.get(city, f"{city}의 날씨 정보를 찾을 수 없습니다.")
```

`parse_docstring=True`로 Google 스타일 `Args:` 문서를 쓰면, 각 파라미터의 설명을 LangChain이 자동으로 뽑아 `args_schema`에 넣어준다 — 별도 Pydantic 스키마를 손으로 안 써도 된다.

```python
search_weather.name                                    # 'search_weather'
search_weather.description                              # docstring 첫 줄
search_weather.args_schema.model_json_schema()           # 자동 생성된 JSON Schema
search_weather.invoke({"city": "서울"})                  # 직접 호출은 () 대신 invoke()
```

### Tool 설계 원칙

| 원칙 | 예 |
|---|---|
| 명확한 이름 | `search_weather` > `func1` |
| 구체적인 설명 | "주어진 도시의 현재 날씨 정보를 검색한다" > "데이터를 가져온다" |
| 타입 힌트 필수 | `city: str` |
| 에러 메시지 | 실패해도 LLM이 이해할 수 있는 메시지를 반환 |

**Tool을 나누는 기준은 API 엔드포인트가 아니라, LLM이 docstring만 보고 언제 쓸지 판단할 수 있는 단위다.** 용도가 다르면 분리(목록 조회 vs 상세 조회), 파라미터 하나 차이면 합쳐도 된다. 너무 잘게 쪼개면 선택 정확도가 떨어지고, 너무 뭉치면 파라미터가 복잡해져 LLM이 헷갈린다.

## Tool 바인딩 — `bind_tools()`

LLM에 "이런 도구를 쓸 수 있다"고 알려주는 것. **바인딩만으로는 Tool이 실행되지 않는다** — LLM은 호출 요청만 만들고, 실제 실행은 애플리케이션 몫이다.

```python
llm_with_tools = llm.bind_tools([search_weather])

response = llm_with_tools.invoke("서울 날씨 알려줘")
response.content      # 비어 있을 수 있음
response.tool_calls   # [{'name': 'search_weather', 'args': {'city': '서울'}, 'id': '...'}]

response2 = llm_with_tools.invoke("안녕하세요")
response2.tool_calls  # [] — Tool이 필요 없으면 그냥 텍스트로 답한다
```

## Google Gen AI SDK vs LangChain `@tool`

| 비교 항목 | Google Gen AI SDK | LangChain `@tool` |
|---|---|---|
| Tool 정의 | JSON 스키마 직접 작성 | Python 함수 + docstring |
| 파라미터 | properties를 수동 정의 | 타입 힌트에서 자동 추출 |
| 결과 확인 | provider 고유 응답 구조 | `AIMessage.tool_calls`로 표준화 |
| 모델 교체 | API별 코드 재작성 | `ChatModel`만 바꾸면 됨 |

## Tool 호출 루프 — Agent의 실체

[Gemini 함수 호출](Gemini_함수호출.md)의 Agent loop와 완전히 같은 구조다: **모델 호출 → Tool 실행 → 결과를 `ToolMessage`로 추가 → 모델 재호출**을 Tool 요청이 없어질 때까지 반복한다.

```python
from langchain_core.messages import HumanMessage, ToolMessage

tools = [search_weather]
tool_map = {t.name: t for t in tools}
llm_with_tools = llm.bind_tools(tools)

def run_agent(user_input: str, max_iterations: int = 5) -> str:
    messages = [HumanMessage(content=user_input)]

    for _ in range(max_iterations):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:      # 더 이상 도구가 필요 없다 = 완료
            return response.content

        for tool_call in response.tool_calls:
            result = tool_map[tool_call["name"]].invoke(tool_call["args"])
            messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            )

    return "최대 반복 횟수를 초과했습니다."
```

`ToolMessage`의 `tool_call_id`는 [Gemini의 `call_id`](Gemini_함수호출.md)와 같은 역할이다 — 실행 결과가 어느 호출에 대한 응답인지 짝지어준다. 모델은 한 번에 여러 Tool을 요청하거나, Tool 결과를 보고 추가 Tool을 요청할 수도 있으므로 `max_iterations`로 무한 호출을 막는다.

## 실전 예제 — TMDB 영화 조회 Agent

목록 조회와 상세 조회를 별도 Tool로 나누면, 모델이 "먼저 목록에서 ID를 얻고 → 그 ID로 상세를 조회"하는 2단계 호출을 스스로 판단해서 수행한다.

```python
@tool(parse_docstring=True)
def get_movies_tool(category: str, size: int = 10):
    """TMDB API를 활용해서 영화 목록을 가져오는 함수.

    Args:
        category: now_playing(상영중), popular(인기), top_rated(평점순), upcoming(개봉예정)
        size: 가져올 영화 개수
    """
    ...

@tool(parse_docstring=True)
def get_movie_by_id_tool(id: int):
    """TMDB API로 영화 ID에 해당하는 상세 정보를 가져오는 함수.

    Args:
        id: TMDB 영화 id
    """
    ...

tools = [get_movies_tool, get_movie_by_id_tool]
tool_map = {t.name: t for t in tools}
llm_with_movie_tool = llm.bind_tools(tools)
```

"상영중인 영화 5개 가져와줘" → "첫 번째 영화의 줄거리 알려줘"를 **같은 세션**에서 물으면, 두 번째 질문은 이전 대화에 남아있는 첫 요청의 목록·ID를 참고해 `get_movie_by_id_tool`을 호출할 수 있다. 하지만 **다른 세션**(새 대화)에서 바로 "첫 번째 영화 줄거리"를 물으면 이전 목록을 모르므로 답할 수 없다 — [LangChain 메모리](LangChain_메모리.md)의 `InMemoryChatMessageHistory`로 세션별 기록을 유지해야 하는 이유다.

```python
memory = {"user-1": InMemoryChatMessageHistory(), "user-2": InMemoryChatMessageHistory()}

def run_agent(user_id: str, request: str, max_attempt: int = 5):
    history = memory[user_id]
    history.add_message(HumanMessage(content=request))

    for _ in range(max_attempt):
        response = llm_with_movie_tool.invoke(history.messages)   # 이 세션의 전체 기록을 전달
        history.add_message(response)

        if not response.tool_calls:
            return response.content

        for tool_call in response.tool_calls:
            result = tool_map[tool_call["name"]].invoke(tool_call["args"])
            history.add_message(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
```

## 참고

- [Gemini 함수 호출](Gemini_함수호출.md) — 같은 개념의 Gemini SDK 버전
- [LangChain 메모리](LangChain_메모리.md) — 세션별 대화 기록 관리
- [LangChain 기초](LangChain_기초.md)
