# MCP 기초

[LangChain Tool과 기본 Agent](LangChain_Tool과Agent.md)에서는 함수를 `@tool`로 감싸 **내 앱 안에** 붙였다. MCP(Model Context Protocol)는 같은 일을 **앱 밖의 서버로 분리하고 연결 방식을 표준화**한다. 날씨 조회를 MCP 서버로 한 번 만들어 두면 LangGraph Agent와 Claude Code가 같은 서버를 그대로 쓴다.

```
LangGraph Agent ──┐
                  ├── 날씨 MCP 서버 ── Tool
Claude Code ──────┘
```

## Tool Calling과 MCP — 층위가 다르다

- **Tool Calling**: LLM이 도구를 쓰기 위한 *모델의 기능* (모델은 호출 요청만 만들고 실행은 앱이 한다).
- **MCP**: AI 앱이 도구·데이터를 쓰기 위한 *앱과 서버 사이의 통신 규약*.

둘은 경쟁 관계가 아니다. MCP 서버의 Tool도 결국 모델의 Tool Calling을 거쳐 호출된다. 달라지는 건 **도구가 어디에 사는가**다.

| 비교 | LangChain `@tool` | MCP 서버의 Tool |
|---|---|---|
| 등록 | Python 함수를 LangChain Tool로 등록 | 서버의 기능을 MCP Tool로 등록 |
| 재사용 | 같은 LangChain 앱에서만 | MCP를 지원하는 어떤 앱에서든 |
| 적합한 경우 | 내 앱에만 필요한 함수·API | 여러 앱이 같은 도구를 공유 / 남이 만든 서버를 가져다 쓸 때 |

## 구성 요소: Host, Client, Server

| 역할 | 하는 일 | 예 |
|---|---|---|
| Host | 모델·대화·도구 사용을 관리하는 AI 앱 | LangGraph Agent 앱, Claude Code |
| Client | Host 안에서 MCP 서버와 통신하는 연결 | `MultiServerMCPClient`가 관리하는 연결 |
| Server | Tool·Resource·Prompt를 제공하는 프로그램 | `weather_server.py` |

**모델은 서버와 직접 통신하지 않는다.** 모델이 호출을 제안하면 Host가 Client를 통해 서버에 실행을 요청한다.

## 서버가 줄 수 있는 세 가지: Tool, Resource, Prompt

| 기능 | 제공하는 것 | 누가 쓰나 | 예 |
|---|---|---|---|
| Tool | 실행 가능한 함수 | 모델이 호출을 제안, 앱이 실행 | 현재 날씨·예보 조회 |
| Resource | URI로 읽는 데이터 | 앱이 필요한 걸 골라 사용 | `weather://cities` (지원 도시 목록) |
| Prompt | 인자를 받는 메시지 템플릿 | 사용자나 앱이 선택 | 도시별 날씨 요약 요청 |

- 서버가 셋을 다 구현할 필요는 없고, Client마다 지원 범위도 다르다.
- **`get_tools()`는 Tool만 가져온다.** Resource와 Prompt는 따로 읽어서 모델에 전달해야 한다. Prompt를 가져오는 것만으로 LLM이 실행되지는 않는다 — 문장만 받아오는 것이다.

## 메시지 구조 — JSON-RPC 2.0

Client와 Server는 JSON-RPC 2.0으로 주고받는다. 연결 초기화 후 `tools/list`로 도구 목록과 입력 형식을 확인하고, `tools/call`로 실행한다.

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
 "params": {"name": "get_current_weather", "arguments": {"city": "서울"}}}
```

| 필드 | 의미 |
|---|---|
| `jsonrpc` | JSON-RPC 형식의 버전 (MCP 버전과 무관) |
| `id` | 어떤 요청에 대한 응답인지 연결하는 식별자 |
| `method` | 작업 이름 (`tools/list`, `tools/call`) |
| `params.name` / `params.arguments` | 실행할 도구와 입력값 |
| `result.content` | 도구가 돌려준 콘텐츠 목록 (텍스트 등) |

## 서버 만들기 — `FastMCP`

`mcp` SDK의 `FastMCP`는 함수에 데코레이터만 붙이면 서버가 된다. `@tool`과 마찬가지로 **함수 이름과 docstring이 Tool의 이름·설명**, 타입 힌트(`Literal["서울","부산","제주"]`)가 입력 스키마가 된다.

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather", host="127.0.0.1", port=8000,
              stateless_http=True, json_response=True)

@mcp.tool()
def get_current_weather(city: City) -> dict:
    """서울·부산·제주 중 한 도시의 현재 기온과 습도를 반환한다."""

@mcp.resource("weather://cities")
def supported_cities() -> str: ...

@mcp.prompt()
def weather_briefing(city: City) -> str: ...

mcp.run(transport="streamable-http")   # http://127.0.0.1:8000/mcp
```

| 코드 | 역할 |
|---|---|
| `FastMCP(...)` | 서버 생성 |
| `@mcp.tool()` | 함수를 Tool로 등록 |
| `@mcp.resource(...)` | 읽을 데이터를 Resource로 등록 |
| `@mcp.prompt()` | 메시지 템플릿을 Prompt로 등록 |
| `mcp.run(...)` | 서버 실행 |

실습 서버는 도시별로 정해 둔 **가상 데이터**를 반환한다. 외부 날씨 API도 API 키도 필요 없어서 MCP 구조만 집중해서 볼 수 있다.

## LangGraph/LangChain에서 쓰기 — `langchain-mcp-adapters`

```bash
pip install "mcp==1.30.0" "langchain-mcp-adapters==0.3.2"
```

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({"weather": {
    "transport": "streamable_http",
    "url": "http://127.0.0.1:8000/mcp",
    "timeout": 10,
}})
tools = await client.get_tools()          # MCP Tool → LangChain Tool 변환
```

1. **서버를 먼저 띄운다** — 별도 터미널에서 `python mcp_examples/weather_server.py`, 실습 중에는 열어 두고 끝나면 `Ctrl+C`.
2. **LLM 없이 Tool을 직접 호출**해 볼 수 있다: `await tool.ainvoke({"city": "서울"})`. 연결 문제와 모델의 도구 선택 문제를 나눠서 확인할 때 유용하다.
3. **Agent에 넘긴다**: `create_agent(model=llm, tools=tools, ...)`.
4. **어댑터 Tool은 비동기**라서 `await agent.ainvoke(...)`를 써야 한다 (`invoke`가 아니다).
5. Resource는 `client.get_resources("weather", uris="weather://cities")`, Prompt는 `client.get_prompt("weather", "weather_briefing", arguments={...})`로 읽고, **문자열로 꺼내 사용자 메시지에 합쳐** Agent에 전달한다.

```python
resources = await client.get_resources("weather", uris="weather://cities")
cities_text = resources[0].as_string()
messages = await client.get_prompt("weather", "weather_briefing", arguments={"city": "서울"})
request = f"지원 도시:\n{cities_text}\n\n{messages[0].text}"
```

시스템 프롬프트에는 "날씨는 반드시 도구로 조회하고, 실패하거나 값이 없으면 추측하지 말고 확인할 수 없다고 안내"를 넣었다. 도구가 있어도 모델이 기억으로 답할 수 있기 때문이다.

## Claude Code에서 같은 서버 쓰기

Claude Code는 MCP Host다. **실행 중인 같은 서버 주소**에 붙이면 된다.

```bash
claude mcp add --transport http --scope local weather http://127.0.0.1:8000/mcp
claude mcp list
claude mcp get weather
```

대화창에서 `/mcp`로 연결 상태와 Tool을 확인한 뒤 요청한다. 도구 실행 승인이 뜨면 호출 이름과 인자를 확인한다. Claude Code는 자체 모델과 인증을 쓰므로 `GOOGLE_API_KEY`를 넘길 필요가 없다.

**핵심: 서버 코드는 하나인데 LangGraph Agent와 Claude Code가 각자 그 Tool을 호출했다.** 이게 `@tool`로는 못 하는, MCP를 쓰는 이유다.

## Smithery와 A2A — 헷갈리기 쉬운 이름들

- **Smithery**: MCP **서버를 찾고 연결하게 돕는 서비스**(웹 검색·문서 조회·브라우저 제어 서버 등). MCP는 통신 규약이고 Smithery는 서버 마켓에 가깝다. 서버에 직접 연결할 수도 있으니 **MCP를 쓰는 데 Smithery가 필수는 아니다.**
- **A2A(Agent2Agent)**: 독립적인 **Agent끼리** 업무를 위임하고 진행 상태·결과를 주고받는 규약.

| 구분 | MCP | A2A |
|---|---|---|
| 연결 대상 | AI 앱 ↔ 도구·데이터 | 독립적인 Agent ↔ Agent |
| 역할 | 외부 기능 호출, 데이터 활용 | 업무 위임, 상태·결과 교환 |
| 예 | 숙소 검색 Tool에 지역·날짜 전달 | 숙소 조사 Agent에게 후보 비교 요청 |

둘은 함께 쓸 수 있다. 여행 계획 Agent ↔ 숙소 조사 Agent는 A2A로, 숙소 조사 Agent가 내부에서 검색 도구를 쓸 때는 MCP로.

## 한 줄 정리

- `@tool` = 내 앱 안의 도구, MCP = 앱 밖 서버로 분리해 **여러 앱이 공유**하는 도구.
- Host(앱) → Client(연결) → Server(Tool/Resource/Prompt). 모델은 서버와 직접 통신하지 않는다.
- `get_tools()`는 Tool만, Resource·Prompt는 따로 읽어서 모델에 넘긴다.
- 어댑터 Tool은 비동기 → `ainvoke`.
