# Gemini 비동기 요청

[비동기 기초](파이썬기초/21_비동기기초.md)에서 본 코루틴과 `asyncio.gather()`를 Gemini API 요청에 그대로 적용한다.

## 왜 LLM API에 비동기가 특히 중요한가

LLM은 응답을 생성하는 데 시간이 오래 걸린다. 서로 **독립적인 질문**을 하나씩 순서대로 요청하면, 첫 번째 답변이 끝나야 두 번째 요청이 시작돼 전체 대기 시간이 길어진다. 여러 문서를 각각 요약하거나, 여러 상품 설명을 생성하거나, 여러 사용자의 질문을 처리할 때 비동기로 동시에 시작하면 전체 처리 시간을 줄일 수 있다.

> ⚠️ 비동기는 **한 요청 자체의 응답 속도를 높이는 게 아니다.** 여러 독립적인 요청의 대기 시간을 겹쳐서 **전체** 처리 시간을 줄이는 방법이다.

FastAPI 같은 비동기 웹 서버에서는 더 중요하다. `async def` 엔드포인트 안에서 LLM 응답을 `await`하면, 기다리는 동안 이벤트 루프가 다른 사용자의 요청을 처리할 수 있어 서버의 동시 처리 효율이 올라간다. 반대로 비동기 엔드포인트 안에서 **동기** LLM 클라이언트를 그대로 호출하면 이벤트 루프 전체가 막혀버리므로, 반드시 비동기 클라이언트를 써야 한다.

## 동기 클라이언트 vs 비동기 클라이언트

```python
client = genai.Client(api_key=api_key)
async_client = client.aio   # 비동기 전용 클라이언트
```

| | 호출 방식 |
|---|---|
| 동기 | `client.interactions.create(...)` |
| 비동기 | `await async_client.interactions.create(...)` |

요청에 전달하는 인자(`model`, `input`, `tools` 등)는 동일하고, **응답을 기다리는 방법만** 다르다.

## Gemini 요청을 코루틴 함수로 만들기

```python
async def ask_gemini(prompt: str) -> str:
    interaction = await async_client.interactions.create(model=model, input=prompt, store=False)
    return interaction.output_text
```

## 순차 실행 vs 함께 실행

```python
prompts = ["LLM을 한 문장으로 설명해 줘.", "임베딩을 한 문장으로 설명해 줘.", "토큰을 한 문장으로 설명해 줘."]

# 순차 — 하나씩 await, 앞 요청이 끝나야 다음 시작
sequential_answers = [await ask_gemini(p) for p in prompts]

# 동시 — gather로 세 요청을 한꺼번에 시작
concurrent_answers = await asyncio.gather(*(ask_gemini(p) for p in prompts))
```

세 개의 독립적인 질문을 동시에 보내면, 가장 오래 걸리는 응답 하나의 시간만큼만 기다리면 된다 — 순차 실행 대비 크게 단축된다. `gather()`의 결과는 항상 **전달한 순서**대로 돌아온다.

## 동시 요청 개수는 제한해야 한다

동시에 너무 많은 요청을 보내면 API 사용량 제한(rate limit)에 걸릴 수 있고, 요청 수만큼 비용도 그대로 발생한다. 실제 서비스에서는 세마포어나 작업 큐로 **동시에 나갈 수 있는 요청 개수 자체를 제한**해야 한다.

## 참고

- [비동기 기초](파이썬기초/21_비동기기초.md)
- [Gemini API 실습](Gemini_API실습.md)
- [Gemini 함수 호출](Gemini_함수호출.md) — 여러 `function_call`을 병렬로 처리할 때도 같은 원리 적용 가능
