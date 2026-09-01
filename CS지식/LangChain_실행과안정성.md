# LangChain 실행과 안정성

[LangChain 기초](LangChain_기초.md)의 체인을 실제 서비스에서 안정적으로 돌리기 위한 기능들 — 토큰 모니터링, 에러 처리, 캐싱, 실행 방식(invoke/batch/stream).

## 토큰 사용량 확인하기

LLM API는 토큰 단위로 과금된다. Gemini 응답의 `usage_metadata`에서 확인할 수 있다.

```python
response = llm.invoke("Python 클래스가 뭐야?")
usage = response.usage_metadata or {}

print(usage.get("input_tokens", 0), usage.get("output_tokens", 0), usage.get("total_tokens", 0))
```

## 에러 처리 — 재시도와 fallback

| 에러 | HTTP 코드 | 원인 | 대응 |
|---|---|---|---|
| Rate Limit | 429 | 짧은 시간에 너무 많은 요청 | 자동 재시도(`max_retries`) |
| Timeout | 408/504 | 서버 응답이 너무 느림 | 타임아웃 설정(`timeout`) |
| Server Error | 500 | 서버 장애 | 재시도 또는 fallback 모델 |
| Auth Error | 401 | API 키가 잘못됨 | `.env` 확인 |

```python
llm = ChatGoogleGenerativeAI(model=MODEL_NAME, max_retries=3, timeout=30)

llm_safe = llm.with_fallbacks([ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")])

try:
    result = llm_safe.invoke("안녕하세요")
except Exception as error:
    print(f"LLM 호출 실패: {error}")   # 개발자 확인용
    print("현재 답변을 생성할 수 없습니다. 잠시 후 다시 시도해주세요.")   # 사용자에게 보여줄 메시지
```

처리 순서는 3단계다.

```
LLM 호출 → 자동 재시도 → fallback 모델 → try/except의 최종 처리
```

- `max_retries`: 실패 시 자동 재시도한다. 대기 시간이 1초 → 2초 → 4초로 늘어나는 **exponential backoff**가 적용된다 — 무한히 빠르게 재시도하면 rate limit이 더 심해지기 때문이다.
- `with_fallbacks()`: 메인 모델이 완전히 실패하면 다른 모델로 자동 전환한다. 실무에서는 비싼 모델을 메인, 저렴한 모델을 백업으로 두는 패턴이 흔하다.
- `try/except`: 재시도·fallback까지 모두 실패한 최종 상황을 처리한다. 실제 서비스에서는 인증 오류·Rate Limit·Timeout처럼 처리 방법이 다른 예외를 최대한 구분하고, API 키 같은 민감한 정보는 사용자 화면이 아니라 서버 로그에 남긴다.

## LLM 응답 캐싱

개발 중 같은 프롬프트를 반복 실행하며 후처리 로직만 고칠 때, 매번 API를 호출하면 비용이 낭비된다.

```python
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache

set_llm_cache(InMemoryCache())

llm.invoke("Python이 뭐야?")   # 첫 호출 — 실제 API 호출
llm.invoke("Python이 뭐야?")   # 두 번째 호출 — 캐시에서 즉시 반환

set_llm_cache(None)   # 실습이 끝나면 꺼둔다
```

## Runnable 실행 방법 — invoke / batch / stream

| 목적 | 동기 | 비동기 |
|---|---|---|
| 입력 하나 실행 | `invoke()` | `ainvoke()` |
| 입력 여러 개 실행 | `batch()` | `abatch()` |
| 응답 스트리밍 | `stream()` | `astream()` |

### `batch()` — 여러 입력을 동시에

입력을 하나씩 `invoke()`하면 앞 응답이 끝나야 다음 요청을 보낸다. `batch()`는 입력별 호출을 동시에 진행해 전체 대기 시간을 줄인다. (Gemini에 하나의 HTTP 요청으로 묶어 보내는 게 아니라, 입력마다 별도 호출이 발생하고 LangChain이 그 호출들을 동시에 실행하는 것이다.)

```python
results = chain.batch([
    {"question": "Python이 뭐야?"},
    {"question": "JavaScript가 뭐야?"},
])

# max_concurrency로 동시 실행 개수 제한 — rate limit 방지에 중요
results = chain.batch(inputs, config={"max_concurrency": 2})
```

결과는 입력과 같은 순서의 리스트로 반환된다.

### `stream()` — 완성을 기다리지 않고 조각 출력

```python
for chunk in chain.stream({"question": "Python의 장점 3가지를 알려줘"}):
    print(chunk, end="", flush=True)
```

체인이 `prompt | llm | StrOutputParser()`라면, 모델은 `AIMessageChunk`를 생성하고 `StrOutputParser`가 각 chunk에서 텍스트를 추출하므로 반복문에서 바로 문자열을 쓸 수 있다. [Gemini 스트리밍](Gemini_스트리밍.md)에서 이벤트 타입을 직접 확인하며 `event.delta.text`를 꺼내던 것과 같은 일을 LangChain이 대신해준다. chunk는 항상 토큰 하나가 아니라 모델·네트워크 상황에 따라 여러 토큰이나 문자 일부일 수 있다.

### `batch()`/`abatch()` vs `asyncio.gather()`

여러 요청을 동시에 실행한다는 점에서 셋 다 비슷해 보이지만, 무엇을 관리하는가가 다르다.

| 상황 | 권장 | 이유 |
|---|---|---|
| 동기 코드에서 같은 체인에 여러 입력 | `batch()` | `await` 없이 Runnable 인터페이스로 처리 |
| 비동기 코드에서 같은 체인에 여러 입력 | `abatch()` | config·callback·tracing·동시성 설정을 LangChain 방식으로 관리 |
| 서로 다른 비동기 작업을 함께 조합 | [`asyncio.gather()`](파이썬기초/21_비동기기초.md) | 서로 다른 coroutine을 자유롭게 구성 |

`abatch()`도 내부적으로는 여러 `ainvoke()`를 병렬 실행한다. 즉 `batch()`가 `gather()`보다 "더 비동기적"이라서 쓰는 게 아니라, 같은 Runnable에 입력 목록을 적용할 때 LangChain의 공통 실행 설정(재시도, 추적 등)을 유지하기 위해 쓰는 것이다.

## Interactions API vs generateContent API

같은 Gemini 모델이라도 호출 경로가 다를 수 있다.

| 코드 | 실제 사용 API |
|---|---|
| `client.interactions.create(...)` | Gemini **Interactions API** (최신 직접 호출 방식) |
| `ChatGoogleGenerativeAI(...).invoke(...)` | Gemini **generateContent API** (LangChain의 Runnable/LCEL 인터페이스가 내부적으로 사용) |

직접 호출은 Gemini의 최신 기능을 바로 쓸 때, LangChain은 여러 구성 요소를 연결할 때 유리하다 — 상황에 맞게 고른다.

## 참고

- [LangChain 기초](LangChain_기초.md)
- [비동기 기초](파이썬기초/21_비동기기초.md)
- [Gemini 스트리밍 응답](Gemini_스트리밍.md)
