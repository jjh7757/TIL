# Gemini Function Calling (함수 호출)

[Gemini API 실습](Gemini_API실습.md)의 기본 대화만으로는 모델이 실시간 재고, 사내 데이터처럼 자기가 모르는 정보를 다룰 수 없다. Function Calling은 모델이 "이 함수를, 이런 인자로 실행해줘"라고 **요청만** 하고, 실제 실행은 우리 애플리케이션이 대신 하도록 역할을 나누는 기능이다.

> 모델은 함수를 직접 볼 수도, 실행할 수도 없다. 실행 권한은 항상 애플리케이션에 있다.

## 전체 흐름

```
사용자 질문 → 모델의 function_call → 애플리케이션이 Python 함수 실행 → function_result 전달 → 모델의 최종 답변
```

## 1. 함수와 "사용설명서(schema)" 준비

```python
def get_product(product_id: str) -> dict:
    """상품 ID로 상품 정보와 재고를 조회합니다."""
    product = PRODUCTS.get(product_id.upper())
    if product is None:
        return {"ok": False, "error": "상품을 찾을 수 없습니다."}
    return {"ok": True, "product_id": product_id.upper(), **product}
```

도구 schema는 [Gemini 구조화 출력](Gemini_구조화출력.md)에서 본 JSON Schema와 같은 형식이다 — 이번엔 "응답 형식"이 아니라 "함수를 호출할 때 넘길 인자 형식"을 정의한다는 점만 다르다.

```python
get_product_tool = {
    "type": "function",
    "name": "get_product",                 # TOOL_FUNCTIONS에 등록할 이름과 반드시 일치해야 함
    "description": "상품 ID를 이용해 상품명, 가격, 현재 재고를 조회합니다.",  # 모델이 도구 선택 근거로 삼는 문장
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": {"type": "string", "description": "조회할 상품 ID. 예: A100"}
        },
        "required": ["product_id"],
    },
}
```

`description`이 모호하면 모델이 엉뚱한 도구를 고르거나 잘못된 인자를 만들 수 있다.

## 2. 모델에게 도구를 알려주고 요청 보내기

```python
interaction = client.interactions.create(
    model=model,
    input="A100 상품의 이름, 가격과 재고를 알려줘.",
    tools=[get_product_tool],
    store=True,
)
```

모델이 도구가 필요하다고 판단하면 `interaction.steps` 안에 `type == "function_call"`인 Step이 담겨 돌아온다. **이 시점엔 아직 아무 함수도 실행되지 않았다** — `step.name`(호출할 함수 이름), `step.id`(이 호출의 고유 ID), `step.arguments`(모델이 만든 인자)만 들어있을 뿐이다.

## 3. 실행 — 허용 목록에 있는 함수만

```python
TOOL_FUNCTIONS = {"get_product": get_product}   # 실제 파이썬 함수를 이름으로 찾기 위한 등록부

for step in interaction.steps:
    if step.type == "function_call":
        if step.name not in TOOL_FUNCTIONS:
            raise ValueError(f"허용되지 않은 도구입니다: {step.name}")
        tool_result = TOOL_FUNCTIONS[step.name](**step.arguments)
```

모델이 보낸 이름이 우리가 미리 등록해둔 `TOOL_FUNCTIONS`에 있을 때만 실행한다 — 모델이 임의의 코드를 실행하게 둘 수는 없기 때문이다.

## 4. 결과를 다시 모델에 전달하기

```python
function_result = {
    "type": "function_result",
    "name": step.name,
    "call_id": step.id,      # 어떤 호출에 대한 응답인지 짝지어주는 꼬리표 — 반드시 일치해야 함
    "result": [{"type": "text", "text": json.dumps(tool_result, ensure_ascii=False)}],
}

final_interaction = client.interactions.create(
    model=model,
    input=[function_result],
    tools=[get_product_tool],
    previous_interaction_id=interaction.id,   # 이전 질문·호출의 맥락과 연결
    store=True,
)
print(final_interaction.output_text)
```

`tool_result`(파이썬 딕셔너리)를 곧바로 넣지 않고 `json.dumps()`로 문자열로 바꿔 `{"type": "text", ...}` Content로 감싸는 이유는, [Gemini API 실습](Gemini_API실습.md)에서 본 것처럼 모든 대화 데이터가 "Step 안에 Content가 담긴" 같은 구조를 따르기 때문이다. 모델은 이 딱딱한 JSON 결과를 받아 "무선 키보드는 39,000원이고 재고가 12개 있습니다" 같은 자연스러운 문장으로 정리해 돌려준다.

## 여러 도구 등록하기 — 선택은 모델이 한다

```python
TOOLS = [search_products_tool, get_product_tool]
TOOL_FUNCTIONS["search_products"] = search_products
```

도구를 여러 개 등록해도 "이럴 땐 이 도구를 써"라고 우리가 지정하지 않는다. 각 도구의 `description`을 비교해서 **모델이 상황에 맞는 도구를 스스로 선택**한다. 그래서 도구별 설명이 서로 겹치지 않게 명확히 구분해서 써야 한다.

## Agent loop — 도구 호출이 여러 번 필요한 경우

"무선 마우스 재고 알려줘"처럼 상품 ID를 모르면 ①검색 도구로 ID를 찾고 → ②그 ID로 재고 조회 도구를 또 호출해야 한다. 이렇게 "질문 → 도구 호출 → 결과 전달"을 여러 바퀴 반복해야 할 수 있어, 반복 처리를 함수로 감싼다.

```python
def run_agent(user_input: str, max_turns: int = 5) -> dict:
    next_input = user_input
    previous_interaction_id = None

    for turn in range(1, max_turns + 1):          # 최대 횟수 제한 — 무한 반복 방지
        interaction = client.interactions.create(
            model=model, input=next_input, tools=TOOLS,
            previous_interaction_id=previous_interaction_id, store=True,
        )
        function_calls = [s for s in interaction.steps if s.type == "function_call"]

        if not function_calls:                     # 더 이상 도구가 필요 없다 = 완료
            return {"ok": True, "answer": interaction.output_text, "turns": turn}

        next_input = []
        for step in function_calls:
            result = execute_tool_call(step)        # 등록된 도구인지 확인 후 실행, 예외는 결과로 감싸 반환
            next_input.append({
                "type": "function_result", "name": step.name, "call_id": step.id,
                "result": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            })

        previous_interaction_id = interaction.id

    return {"ok": False, "error": "최대 반복 횟수를 초과했습니다."}
```

`max_turns`로 상한을 두지 않으면 모델이 계속 도구만 호출하고 답을 안 줄 때 비용과 시간이 무한히 늘어날 수 있다. `execute_tool_call`은 [예외 처리](파이썬기초/14_예외처리.md)로 감싸서, 등록되지 않은 도구나 실행 중 오류도 프로그램을 죽이지 않고 결과 형태(`{"ok": False, "error": ...}`)로 되돌린다.

## 자주 하는 실수

- **셀 재실행으로 도구 중복 등록**: `TOOLS.append(tool)`을 노트북 셀에서 여러 번 실행하면 같은 도구가 리스트에 중복돼 `Duplicate function declaration found` 에러가 난다. `TOOLS = [...]`로 매번 새로 정의하거나, 추가 전에 이미 있는지 확인한다.
- **`TOOL_FUNCTIONS` 등록 키가 도구 이름과 다름**: `TOOL_FUNCTIONS["func"] = func`처럼 임의의 이름으로 등록하면, 나중에 `TOOL_FUNCTIONS[step.name]`으로 찾을 때(`step.name`은 실제 도구 이름) `KeyError`가 난다 — 등록 키는 반드시 `tool["name"]`과 같아야 한다.
- **함수 호출이 없을 수도 있다는 걸 놓침**: 모델이 도구 없이 바로 답할 수도 있으므로, `function_call`을 찾기 전에 존재 여부를 먼저 확인해야 다음 단계에서 `NameError`가 나지 않는다.

## 참고

- [Gemini API 실습](Gemini_API실습.md)
- [Gemini 구조화 출력](Gemini_구조화출력.md) — 도구 schema와 같은 JSON Schema 문법
- [예외 처리](파이썬기초/14_예외처리.md)
- [Gemini 내장 도구](Gemini_내장도구.md)
