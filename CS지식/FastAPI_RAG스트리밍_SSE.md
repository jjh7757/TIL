# RAG Agent 연결과 SSE 스트리밍

검색 → 답변 생성을 순서대로 수행하는 **RAG 그래프**를 `fastapi_agent`에 연결합니다. chat 도메인의 Service가 그래프를 실행하고, **SSE**로 답변을 생성되는 대로 전달합니다. 사용자는 화면에서 생성 중인 답변, 참고 문서, 실행 시간을 봅니다.

## 실행 흐름

```
브라우저          Chat Router              RagChatService               RAG 그래프
   │ POST /chat/rag/stream │                       │                          │
   │──────────────────────▶│ JWT 인증·요청 검증     │                          │
   │                       │ stream_rag(agent, q) ─▶│ astream(question) ──────▶│
   │                       │                       │◀── 검색된 문서 ──────────│
   │◀── SSE sources ───────│◀── sources 데이터 ─────│                          │
   │                       │                       │  ┌ loop: 답변 생성 ────┐ │
   │◀── SSE token ─────────│◀── token 데이터 ───────│◀─┤ 답변 조각           │─│
   │                       │                       │  └─────────────────────┘ │
   │◀── SSE done ──────────│◀── done 데이터 ────────│ (최종 답변 + 실행 시간)  │
```

## 준비: Chroma에 문서 적재

질문과 **의미가 비슷한** 문서를 찾으려면 문서를 벡터로 바꿔 저장해야 합니다. `.env`에 `GEMINI_API_KEY`를 설정하고:

```bash
uv run rag-ingest
```

- PDF를 읽어 청크로 나누고, 각 청크를 임베딩해 `./chroma_db`의 `spri_ai_brief` 컬렉션에 저장
- 그래프를 **생성할 때** 이 컬렉션에 연결하므로 **서버 실행 전에** 적재를 마쳐야 한다
- 다시 실행하면 기존 컬렉션을 지우고 새로 적재

## 사용할 RAG 그래프

`agents.rag`의 `create_rag_agent()`는 검색기와 Gemini 모델을 연결한 그래프를 반환합니다.

```
START → retrieve → generate → END
```

검색 여부와 순서가 코드로 정해진 **고정 워크플로**라 모든 질문에 검색과 생성을 차례로 수행합니다.

| 상태 | 내용 |
|------|------|
| `question` | 사용자 질문 |
| `documents` | 검색된 `Document` 목록 |
| `answer` | 문서를 근거로 생성한 답변 |

Service는 질문을 넘기고 검색 결과·생성 중인 답변을 읽으며, **HTTP 응답 형식은 Router**가 구성합니다.

---

## SSE와 비동기 스트리밍

### 일반 응답 vs 스트리밍 응답

모델의 답변 생성에는 시간이 걸립니다. 일반 JSON은 생성이 **끝난 뒤** 한 번에 보내고, 스트리밍은 **연결을 유지하며** 생성된 내용을 나눠 보냅니다.

| 구분 | 일반 JSON | SSE |
|------|-----------|-----|
| Content-Type | `application/json` | `text/event-stream` |
| 본문 | 완성된 JSON 하나 | 순서대로 이어지는 텍스트 이벤트 |
| 화면 표시 | 다 받은 뒤 | 이벤트를 받을 때마다 갱신 |
| 본문 읽기 | `response.json()` | `response.body` 스트림 읽기 |

**SSE(Server-Sent Events)** 는 서버가 클라이언트로 이벤트를 보내는 형식입니다. 하나의 HTTP 응답으로 답변 조각과 진행 상태를 계속 전달합니다. (WebSocket과 달리 **서버→클라이언트 단방향**이며 일반 HTTP 위에서 동작)

### 이벤트 형식

```
event: token
data: {"content":"AI 산업에서는 "}

event: token
data: {"content":"인프라 투자가 확대되고 있습니다."}

```

| 요소 | 의미 |
|------|------|
| `event:` | 클라이언트가 구분할 이벤트 이름 |
| `data:` | 전달할 데이터 (이 API는 JSON 문자열) |
| `\n\n` (빈 줄) | 이벤트 하나의 끝 |

`data`를 JSON으로 직렬화하면 답변 속 줄바꿈이 문자열 안의 `\n`(두 글자)으로 표현되어 **이벤트 경계와 섞이지 않습니다**.

### 이벤트 종류 (서버–프론트엔드 약속)

| 이벤트 | 데이터 예시 | 화면 처리 |
|--------|-------------|-----------|
| `status` | `{"message": "문서를 검색하고 있습니다."}` | 진행 상태 표시 |
| `sources` | `{"sources": [{"id": 1, "source": "보고서.pdf", "page_number": 3}]}` | 참고 문서 표시 |
| `token` | `{"content": "답변 조각"}` | 현재 답변에 **덧붙이기** |
| `done` | `{"answer": "최종 답변", "sources": [], "elapsed_ms": 1320}` | 최종 결과 반영, 수신 종료 |
| `error` | `{"message": "답변 생성 중 오류가 발생했습니다."}` | 오류 표시, 수신 종료 |

- `token`은 모델이 준 텍스트 조각. 한 조각에 여러 글자가 들어 있을 수 있다
- `sources`의 `id`는 답변의 `[1]`, `[2]` 인용 번호에 대응

### `async for`와 `yield` — 비동기 제너레이터

```python
async def events():
    yield "검색 시작"
    yield "답변 생성"
    yield "완료"


async for event in events():
    print(event)
```

- `async def` 안에 `yield`가 있으면 **비동기 제너레이터**
- `events()` 호출 시 제너레이터 객체만 만들어지고, `async for`가 다음 값을 요청할 때 실행 → `yield`에서 값을 주고 **멈춤** → 다음 요청 때 이어서 실행
- `await`는 결과 **하나**를 기다리고, `async for`는 비동기 반복자가 만드는 값을 **차례로** 받는다
- `StreamingResponse`에 제너레이터를 넘기면 FastAPI가 이 반복을 수행하며 값을 응답 본문으로 보낸다

### 동기·비동기 호출과 스트리밍

| 용도 | 동기 | 비동기 |
|------|------|--------|
| 끝난 뒤 최종 결과 받기 | `invoke()` | `await ainvoke()` |
| 실행 중 생성되는 값을 차례로 받기 | `for ... in stream(...)` | `async for ... in astream(...)` |

**비동기와 스트리밍은 다른 개념**입니다. `ainvoke()`는 비동기로 실행하지만 완성된 결과를 반환하고, `astream()`은 중간 결과를 차례로 전달합니다. 이 API는 **노드 안에서 `await model.ainvoke(...)`**, **Service에서 `agent.astream(...)`** 을 씁니다.

### LangGraph 스트림 모드

| 모드 | 받는 시점과 내용 | 용도 |
|------|------------------|------|
| `messages` | 모델이 생성하는 동안 `(메시지 조각, 메타데이터)` | 답변 조각 즉시 표시 |
| `updates` | 각 노드 **완료 시** 그 노드가 반환한 상태 변경 | 검색 문서, 최종 답변 확인 |

```python
async for mode, data in agent.astream(
    {"question": question},
    stream_mode=["messages", "updates"],
):
    if mode == "messages":
        chunk, metadata = data
        if metadata["langgraph_node"] == "generate" and chunk.text:
            print(chunk.text, end="", flush=True)
    elif mode == "updates":
        print(data)
```

- 모드를 여러 개 지정하면 매번 `(mode, data)` 튜플을 받는다
- `messages`: `metadata["langgraph_node"]`로 **어느 노드가 만든 조각인지** 걸러 `generate`의 텍스트만 사용
- `updates`: 노드 이름이 키. `{"retrieve": {"documents": [...]}}`, `{"generate": {"answer": "..."}}`

### 노드는 `ainvoke()`인데 토큰이 스트리밍되는 이유

노드 안에서 `model.invoke()`/`ainvoke()`를 써도, 그래프를 `stream_mode="messages"`로 실행하면 **생성 중인 토큰을 받을 수 있습니다**. 노드는 완성된 응답을 기다리지만, 그동안 LangGraph가 모델의 토큰 생성 이벤트를 받아 그래프 **바깥의 `messages` 스트림**으로 흘려보냅니다. 따라서 노드 안에서 `model.astream()`을 직접 순회할 필요가 없습니다.

- 조건: 스트리밍을 지원하는 LangChain 채팅 모델 + 모델 스트리밍을 끄지 않았을 것
- `"updates"`만 지정하면 노드가 끝난 뒤의 결과만 온다 → 토큰을 받으려면 `"messages"` 필수

---

## chat 도메인 구성

| 파일 | 처리 |
|------|------|
| `schemas.py` | 질문 요청 형식 |
| `rag_service.py` | 그래프 출력 → (이벤트 이름, 데이터) |
| `router.py` | 이벤트 → SSE 본문으로 직렬화해 전송 |

```python
# schemas.py
class RagChatRequest(BaseModel):
    question: str = Field(min_length=1)
```

### 앱 시작 시 그래프 생성과 공유

검색기·모델 클라이언트·그래프를 **요청마다 만들지 않도록** lifespan에서 한 번 생성해 `app.state`에 보관합니다.

```python
# main.py (발췌)
from agents import create_rag_agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.rag_agent = create_rag_agent()
        yield
    finally:
        await engine.dispose()
```

- `app.state`: 앱의 요청들이 **공유할 객체**를 두는 공간
- 그래프는 **서버 프로세스마다** 한 번 생성. 워커를 여러 개 띄우면 각자 자기 그래프를 가진다
- 공유하는 것은 **실행 가능한 그래프 객체**일 뿐, 질문·문서·답변은 각 `astream()` 호출의 상태로 따로 관리된다

| 표현 | 의미 |
|------|------|
| `request` | 현재 HTTP 요청 객체 (`request: Request`로 선언하면 FastAPI가 주입) |
| `request.app` | 요청을 처리하는 FastAPI 앱 |
| `request.app.state.rag_agent` | 시작 시 보관한 RAG 그래프 |

### Service — 그래프 출력을 이벤트로 변환

| 시점 / 입력 | 처리 |
|-------------|------|
| 실행 시작 | `status` (검색 중) |
| `updates`의 `retrieve` | 문서 메타데이터 → 출처 목록 `sources`, `status` (생성 중) |
| `messages`의 `generate` | 답변 조각 → `token` |
| `updates`의 `generate` | 최종 답변을 `answer`에 보관 |
| 반복 종료 | `done` (최종 답변·출처·경과 시간) |

```python
# rag_service.py
from time import perf_counter

class RagChatService:
    async def stream_rag(self, agent: CompiledStateGraph, question: str):
        started = perf_counter()
        answer = ""
        sources = []

        yield "status", {"message": "문서를 검색하고 있습니다."}

        async for mode, data in agent.astream(
            {"question": question},
            stream_mode=["messages", "updates"],
        ):
            if mode == "messages":
                chunk, metadata = data
                if metadata["langgraph_node"] == "generate" and chunk.text:
                    yield "token", {"content": chunk.text}

            elif mode == "updates":
                if "retrieve" in data:
                    documents = data["retrieve"]["documents"]
                    sources = [
                        {
                            "id": index,
                            "source": document.metadata["source"],
                            "page_number": document.metadata["page_number"],
                        }
                        for index, document in enumerate(documents, start=1)
                    ]
                    yield "sources", {"sources": sources}
                    yield "status", {"message": "답변을 생성하고 있습니다."}

                if "generate" in data:
                    answer = data["generate"]["answer"]

        yield "done", {
            "answer": answer,
            "sources": sources,
            "elapsed_ms": round((perf_counter() - started) * 1000),
        }


rag_chat_service = RagChatService()
```

- `enumerate(documents, start=1)`로 1부터 번호 → `generate` 노드도 **같은 순서로** 문서에 번호를 붙이므로 `id`가 답변의 `[1]`, `[2]`와 맞는다
- `source`, `page_number`는 **적재 시 설정한 메타데이터**
- `token`은 즉시 보내고, `done`에는 **노드가 반환한 최종 답변**을 넣어 스트림을 다 읽은 뒤 **한 번만** 전송
- `perf_counter()`: 경과 시간 측정용 단조 시계 (시스템 시각 변경의 영향을 받지 않음)
- Service는 HTTP를 모르고 `(이름, dict)`만 내보낸다 → SSE 문자열 변환은 Router 몫

### Router — SSE 응답

```python
# router.py
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)],     # 라우터 전체에 인증 적용
    responses=error_responses(401, 422),
)


def format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post(
    "/rag/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def stream_rag(data: RagChatRequest, request: Request):
    agent = request.app.state.rag_agent

    async def events():
        try:
            async for event, payload in rag_chat_service.stream_rag(agent, data.question):
                yield format_sse(event, payload)
        except Exception:
            logger.exception("RAG 스트리밍 실행 실패")
            yield format_sse("error", {"message": "답변 생성 중 오류가 발생했습니다."})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

| 부분 | 역할 |
|------|------|
| `dependencies=[Depends(get_current_user)]` | 반환값이 필요 없는 의존성을 라우터 전체에 적용. **스트리밍 시작 전** JWT 검사 |
| 내부 함수 `events()` | 바깥의 `agent`, `data.question`을 사용(클로저). Service 튜플을 SSE 문자열로 변환 |
| `try/except`가 `events()` **안에** 있는 이유 | 본문은 `StreamingResponse`가 제너레이터를 순회할 때 생성됨 → 그래프 실행 예외도 그때 발생하므로 핸들러 함수의 try로는 못 잡는다 |
| `ensure_ascii=False` | 한글을 `\uXXXX`가 아닌 그대로 표현 |
| `media_type` | 실제 응답의 Content-Type. 데코레이터의 `responses`는 **OpenAPI 문서 표시용** |
| `Cache-Control: no-cache` | 캐시된 응답을 그대로 재사용하지 않게 |
| `X-Accel-Buffering: no` | Nginx에 버퍼링 해제 요청 → 조각이 모였다 한꺼번에 가지 않게 |

```python
# main.py
from fastapi_agent.domains.chat.router import router as chat_router
app.include_router(chat_router)
```

### 응답 시작 전과 후의 오류

| 시점 | 처리 |
|------|------|
| 스트리밍 시작 전 인증 실패 | 401 + 공통 JSON 오류 응답 |
| 스트리밍 시작 전 요청 검증 실패 | 422 + 공통 JSON 오류 응답 |
| 스트리밍 시작 **후** 그래프 실행 실패 | 서버 로그 + `error` **이벤트** |

응답 헤더를 보내는 순간 **HTTP 상태 코드(200)가 확정**됩니다. 이후 실패는 상태 코드로 알릴 수 없으므로, 연결이 살아 있다면 `error` 이벤트로 보냅니다. ([공통 응답과 예외 처리](FastAPI_공통응답_예외처리.md)의 전역 핸들러는 시작 전 오류만 담당)

---

## 프론트엔드에서 스트림 받기

### 인증된 POST 요청

```js
const response = await fetch(`${API_BASE_URL}/chat/rag/stream`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify({ question }),
})
```

`fetch()`는 **응답 헤더를 받으면** 반환하고, 이후 `response.body`에서 이벤트를 계속 읽습니다. 브라우저 기본 `EventSource`는 GET만 되고 헤더를 못 붙이므로, POST 본문과 `Authorization`이 필요한 여기서는 `fetch()`로 직접 읽습니다.

### 청크와 이벤트 경계 — `consumeSSE()`

네트워크 청크는 이벤트 경계와 무관합니다. 한 이벤트가 여러 청크로 쪼개지거나, 한 청크에 여러 이벤트가 오거나, **한글의 UTF-8 바이트가 중간에서 잘릴** 수 있습니다. `frontend/src/api/stream.js`의 `consumeSSE()`는 **바이트 → 문자열 → 줄 → 이벤트** 순으로 읽습니다.

```js
const reader = body.getReader()
const decoder = new TextDecoder()
let buffer = ''

while (true) {
  const { value, done } = await reader.read()
  buffer += decoder.decode(value, { stream: !done })
  let match
  while ((match = /[\r\n]/.exec(buffer))) {
    const index = match.index
    if (!done && buffer[index] === '\r' && index === buffer.length - 1) break
    const width = buffer[index] === '\r' && buffer[index + 1] === '\n' ? 2 : 1
    const content = buffer.slice(0, index)
    buffer = buffer.slice(index + width)
    if (line(content)) return
  }
  if (done) return
}
```

| 부분 | 역할 |
|------|------|
| `reader.read()` | 이번에 받은 바이트 배열 `value`와 종료 여부 `done` |
| `decode(value, { stream: true })` | 미완성 문자의 바이트를 **다음 호출까지 보관** (한글 깨짐 방지). 마지막엔 `stream: false`로 남은 바이트 처리 |
| 바깥 `while` | 네트워크 청크 받기 |
| 안쪽 `while` | 버퍼에서 **완성된 줄을 모두** 꺼냄. 끝나지 않은 줄은 버퍼에 남음 |
| 끝이 `\r`이면 `break` | 다음 청크에 `\n`이 이어질 수 있어(`\r\n`) 대기 |
| `width` | 줄바꿈 길이 (`\r\n`이면 2, `\n`·`\r`이면 1) |

`line()`이 줄을 모아 이벤트를 만드는 규칙:

| 받은 줄 | 처리 |
|---------|------|
| `event: token` | 현재 이벤트 이름 저장 |
| `data: {...}` | `data:` 뒤 문자열을 배열에 추가 |
| 빈 줄 | 모은 데이터를 줄바꿈으로 합쳐 `{ event, data }`를 콜백에 전달, 다음 이벤트 준비 |
| `:`로 시작 | SSE 주석 (무시) |

콜백이 `true`를 반환하면 읽기를 끝내고, `finally`에서 `reader.cancel()`, `reader.releaseLock()`으로 정리합니다.

### 이벤트 처리와 최종 결과 — `streamRequest()`

```js
const result = await streamRequest('/chat/rag/stream', {
  body: { question },
  token,
  onEvent(event, data) {
    if (event === 'token') console.log(data.content)
  },
})

console.log(result.answer)
```

`await`로 완료를 기다리는 **동안에도** `onEvent`는 이벤트가 올 때마다 실행됩니다. 내부에서는 `data`를 `JSON.parse()`한 뒤:

```js
onEvent?.(event, payload)                         // 콜백이 있으면 실행
if (event === 'done') { result = payload; return true }   // 결과 보관 후 종료
return false
```

> `reader.read()`의 `done` = 응답 본문을 **끝까지 읽음**, SSE `done` 이벤트 = 서버가 **답변 생성을 완료함**. 본문이 끝났는데 `result`가 비어 있으면 **미완료 응답**으로 처리한다.

| 실패 상황 | 처리 |
|-----------|------|
| HTTP 오류 응답 | JSON 오류 본문을 읽어 `ApiError` |
| SSE `error` 이벤트 | 이벤트의 안내 문구로 `ApiError` |
| `done` 없이 연결 종료 | "답변 완료 전 연결이 끊김" 오류 |
| 요청 시작 후 120초 경과 | 내부 `AbortController`로 취소, 시간 초과 오류 |

`finally`에서 제한 시간 타이머와 취소 리스너를 정리합니다.

### `ai.ask()`

```js
// frontend/src/api/ai.js
ask: async (question, token, signal, onEvent) => {
  const data = await streamRequest('/chat/rag/stream', {
    body: { question }, token, signal, onEvent,
  })
  if (typeof data?.answer !== 'string') throw new ApiError('답변을 읽을 수 없습니다.', 0)
  return data
},
```

`token`은 인증, `signal`은 취소, `onEvent`는 중간 결과 전달, 반환값은 `done`의 최종 결과입니다.

### 화면: 토큰 누적과 최종 반영 (`RagPage.jsx` 핵심)

```jsx
const requestRef = useRef(null)
useEffect(() => () => requestRef.current?.abort(), [])   // 화면을 떠나면 수신 취소

async function submit(event) {
  event.preventDefault()
  if (loading || !question.trim()) return

  const controller = new AbortController()
  requestRef.current = controller
  setLoading(true); setAnswer(''); setSources([]); setError(''); setElapsed(null)
  setStatus('요청하고 있습니다.')

  try {
    const result = await ai.ask(
      question.trim(), token, controller.signal,
      (event, data) => {
        if (event === 'status') setStatus(data.message)
        if (event === 'sources') setSources(data.sources)
        if (event === 'token') setAnswer(current => current + data.content)
      },
    )
    if (!controller.signal.aborted) {
      setAnswer(result.answer)            // 누적 텍스트를 최종 답변으로 교체
      setSources(result.sources)
      setElapsed(result.elapsed_ms)
      setStatus('완료')
    }
  } catch (reason) {
    if (!controller.signal.aborted) {
      setError(reason.message)            // 부분 답변은 유지하고 오류 안내 추가
      setStatus('응답 중단')
    }
  } finally {
    if (!controller.signal.aborted) setLoading(false)
  }
}
```

```jsx
<div style={{ whiteSpace: 'pre-wrap' }}>{answer}</div>
<ul>
  {sources.map(source => (
    <li key={source.id}>[{source.id}] {source.source} · {source.page_number}쪽</li>
  ))}
</ul>
{elapsed !== null && <p>실행 시간: {(elapsed / 1000).toFixed(1)}초</p>}
```

- `status`·`sources`는 상태를 **교체**, `token`은 **누적**
- `setAnswer(current => current + data.content)` — **함수형 갱신**. `setAnswer(answer + ...)`처럼 쓰면 콜백이 만들어질 때의 옛 `answer`를 참조해 조각이 유실된다. `current`에는 React가 처리 중인 **최신 상태**가 들어온다
- `useRef`: 렌더링이 바뀌어도 **같은 보관 공간 유지** (값이 바뀌어도 재렌더링 안 함)
- `useEffect`가 반환한 함수는 컴포넌트가 **제거될 때** 실행되는 정리 함수 → `abort()`로 수신 취소, `signal.aborted`로 이후의 상태 변경을 건너뜀
- `whiteSpace: 'pre-wrap'`: 답변의 줄바꿈을 화면에 그대로 표시

## 실행 확인

프론트엔드 `.env`에 `VITE_API_BASE_URL=http://127.0.0.1:8000`, 백엔드 CORS에 프론트엔드 출처와 `Authorization`·`Content-Type` 허용 ([CORS](FastAPI_프론트엔드연결_CORS.md)).

- 로그인 후 질문 → 검색 상태와 출처 표시
- 생성 중 답변 텍스트가 점점 늘어남
- `done` 수신 → 최종 답변·실행 시간 표시, 전송 버튼 다시 활성화
- 답변의 인용 번호와 참고 문서 목록을 대조해 근거 확인
- 인증 오류·생성 실패·연결 중단 시 오류 안내
