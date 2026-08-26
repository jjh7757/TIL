# Gemini 내장 도구(Built-in Tools)

[Function Calling](Gemini_함수호출.md)은 우리가 직접 만든 함수를 모델이 호출하게 하는 방식이었다. 내장 도구는 검색·코드 실행처럼 Google이 이미 만들어둔 기능을 등록만 하면 되고, **실행도 Gemini 서버가 대신 해준다** — 우리가 함수를 실행하거나 결과를 다시 전달할 필요가 없다.

## 내장 도구 vs 커스텀 Function Calling

| | 내장 도구 | 커스텀 Function Calling |
|---|---|---|
| 제공자 | Google | 개발자 |
| 도구 정의 | 종류만 등록 (`{"type": "code_execution"}`) | 함수 설명 + 매개변수 schema 직접 작성 |
| 실행 위치 | Gemini 서버 | 우리 애플리케이션 |
| 결과 전달 | Gemini가 자동 처리 | 애플리케이션이 `function_result`로 직접 전달 |
| 예 | 웹 검색, 코드 실행, 지도 | 주문 조회, 사내 API, 예약 처리 |

## Code Execution — 모델이 직접 코드를 만들고 실행

```python
code_interaction = client.interactions.create(
    model=model,
    input="1부터 100까지 자연수 중 3의 배수이면서 5의 배수인 수를 Python으로 구하고, 그 합도 알려줘.",
    tools=[{"type": "code_execution"}],
)
print(code_interaction.output_text)
```

단순히 코드를 "적어주는" 게 아니라 Google 서버의 실행 환경에서 **실제로 실행**한 결과를 사용한다. `steps`를 보면 과정이 그대로 남아있다.

```python
for step in code_interaction.steps:
    if step.type == "code_execution_call":
        print("실행 코드:", step.arguments.code)
    elif step.type == "code_execution_result":
        print("실행 결과:", step.result)
```

## Google Search — 최신 정보로 답하기

모델이 학습한 지식만으로는 오늘 날씨나 최근 뉴스처럼 계속 바뀌는 정보를 정확히 답할 수 없다. `google_search`를 등록하면 모델이 필요한 검색어를 스스로 만들고, 검색 결과를 근거로 답한다.

```python
search_interaction = client.interactions.create(
    model=model,
    input="오늘 기준으로 Python 공식 홈페이지에 공개된 최신 안정 버전을 찾아서 버전과 출시일을 알려줘. 출처도 함께 제시해 줘.",
    tools=[{"type": "google_search", "search_types": ["web_search"]}],
)
```

답변에 쓰인 출처는 `model_output` Step의 `content` 안 `annotations`에 `url_citation` 형태로 담긴다.

```python
for step in search_interaction.steps:
    if step.type != "model_output":
        continue
    for block in step.content:
        for annotation in getattr(block, "annotations", None) or []:
            if annotation.type == "url_citation":
                print(annotation.title, annotation.url)
```

## 여러 도구를 함께 쓰기

`tools` 리스트에 여러 내장 도구를 같이 넣으면, 모델이 상황에 맞춰 필요한 도구들을 순서대로 조합해 쓴다.

```python
combined_interaction = client.interactions.create(
    model=model,
    input="오늘 기준 원/달러 환율을 검색한 뒤, 150달러가 몇 원인지 계산해 줘.",
    tools=[
        {"type": "google_search", "search_types": ["web_search"]},
        {"type": "code_execution"},
    ],
)
```
(예: 검색으로 환율을 알아낸 뒤, 계산은 code_execution으로 처리)

## 내장 도구 + 커스텀 함수 함께 쓰기

Gemini 3 모델부터는 내장 도구와 [커스텀 함수](Gemini_함수호출.md)를 하나의 `tools` 목록에 같이 등록할 수 있다. 내장 도구는 서버에서 자동 실행되지만, 커스텀 함수는 여전히 우리가 실행하고 `function_result`를 돌려줘야 한다.

```python
mixed_tools = [
    {"type": "google_search", "search_types": ["web_search"]},
    get_store_stock_tool,   # 우리가 만든 커스텀 함수 도구
]

mixed_interaction = client.interactions.create(
    model=model,
    input="오늘 서울 날씨를 검색하고, 우리 매장의 우산과 우비 재고를 확인해서 무엇을 준비할 수 있는지 답해 줘.",
    tools=mixed_tools,
    store=True,
)

function_calls = [s for s in mixed_interaction.steps if s.type == "function_call"]
if function_calls:
    function_results = [
        {
            "type": "function_result",
            "name": fc.name,
            "call_id": fc.id,
            "result": [{"type": "text", "text": json.dumps(get_store_stock(**fc.arguments), ensure_ascii=False)}],
        }
        for fc in function_calls
    ]
    final = client.interactions.create(
        model=model, input=function_results, tools=mixed_tools,
        previous_interaction_id=mixed_interaction.id, store=True,
    )
    print(final.output_text)
```

흐름은 이렇다: `Google Search 자동 실행(서버가 처리)` → `커스텀 함수의 function_call 반환(우리가 처리해야 함)` → `우리가 실행한 결과를 function_result로 전달` → `최종 답변`. 한 응답에 `function_call`이 여러 개 담길 수 있으므로 리스트로 모아 각각의 `call_id`에 맞는 결과를 짝지어 보낸다.

## 전체 흐름 정리

```
사용자 질문 → Gemini가 필요한 도구 선택 → Gemini 서버에서 도구 실행 → 실행 결과를 활용한 최종 답변
```

내장 도구는 [Function Calling](Gemini_함수호출.md)과 달리 우리가 함수를 실행하거나 결과를 전달할 필요가 없다. 다만 모든 질문에 도구가 필요한 것은 아니므로, `steps`와 출처(`annotations`)를 확인해 실제로 도구가 쓰였는지·근거가 무엇인지 점검하는 습관이 필요하다.

## 참고

- [Gemini 함수 호출](Gemini_함수호출.md)
- [Gemini API 실습](Gemini_API실습.md)
