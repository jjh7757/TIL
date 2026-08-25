# Gemini Structured Output — JSON으로 응답 강제하기

[Gemini API 실습](Gemini_API실습.md)의 `output_text`는 자연스러운 문장이라 사람이 읽기엔 좋지만, 뒤이은 코드가 필요한 값을 다시 파싱해야 한다. 표현이나 문장 순서가 조금만 달라져도 후속 처리가 깨지기 쉽다. Structured Output은 응답 자체를 정해진 JSON 구조로 강제해서 이 문제를 없앤다.

```bash
pip install pydantic
```

## Pydantic으로 원하는 구조 정의하기

Pydantic은 타입 힌트로 데이터 구조를 선언하고, 실제 값이 그 조건에 맞는지 **검증**까지 해주는 라이브러리다. 이 모델로부터 JSON Schema를 자동 생성해서, "모델 코드"와 "Gemini에게 알려줄 스키마"를 한곳에서 관리한다.

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationError

class ReviewAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")   # 선언하지 않은 필드가 오면 검증 실패

    sentiment: Literal["positive", "neutral", "negative"]
    summary: str = Field(max_length=30)
    keywords: list[str] = Field(min_length=2, max_length=2)

review_schema = ReviewAnalysis.model_json_schema()
```

| 코드 | 역할 |
|---|---|
| `BaseModel` | Pydantic 데이터 모델의 기본 클래스 |
| `Literal[...]` | 정해진 문자열 중 하나로 값을 제한 |
| `Field(...)` | 길이·개수 등 추가 제약 조건 |
| `ConfigDict(extra="forbid")` | 정의 밖 필드가 들어오면 검증 실패 처리 |
| `model_json_schema()` | 모델을 JSON Schema(dict)로 변환 |

생성된 JSON Schema 안에서 `type`은 자료형, `properties`는 필드 정의, `enum`은 허용값, `items`는 배열 원소 타입, `required`는 필수 필드, `additionalProperties: false`는 정의 외 필드 금지를 의미한다.

## 모델 조건에 맞지 않는 값 검증하기

JSON 문법이 맞아도 값이 규칙과 다르면(허용되지 않은 값, 길이 초과, 정의되지 않은 필드 등) `ValidationError`가 발생한다.

```python
import json

invalid_json = json.dumps({
    "sentiment": "happy",   # Literal에 없는 값
    "summary": "삼십 자 제한을 넘기기 위해 일부러 아주 길게 작성한 문장입니다.",
    "keywords": ["속도"],   # 2개가 아님
    "rating": 5,            # 정의되지 않은 필드
}, ensure_ascii=False)

try:
    ReviewAnalysis.model_validate_json(invalid_json)
except ValidationError as error:
    print(error.errors())
```

## Structured Output 요청 보내기

`response_format`으로 응답의 MIME type과 스키마를 함께 지정한다. MIME type(`application/json`)은 "JSON 문법에 맞는 텍스트로 만들라"는 지시일 뿐, 필드 구조까지 정하는 것은 `schema`의 역할이다.

```python
structured = client.interactions.create(
    model=model,
    input=f"다음 후기를 분석하세요. summary는 30자 이내, keywords는 2개만.\n\n[후기]\n{review}",
    response_format={
        "type": "text",
        "mime_type": "application/json",
        "schema": review_schema,
    },
    store=False,
)
```

`structured.output_text`는 JSON처럼 보여도 아직 `str`이다. 실제로 쓰려면 파싱이 필요하다.

## 파싱과 검증

```python
# 1. 단순 파싱 — json.loads()
parsed = json.loads(structured.output_text)
print(parsed["sentiment"])

# 2. 파싱 + 검증을 한 번에 — Pydantic
try:
    result = ReviewAnalysis.model_validate_json(structured.output_text)
except ValidationError as error:
    print("검증 실패:", error.errors())
else:
    print(result.sentiment)
    print(result.model_dump())   # 다시 dict로
```

`json.loads()`는 JSON 문법만 Python 값으로 바꿔줄 뿐, 필드가 빠지거나 값이 허용 범위를 벗어나도 알려주지 않는다. `model_validate_json()`은 파싱과 동시에 Pydantic 모델의 조건(타입, `Literal`, `Field` 제약)까지 검사한다.

> Structured Output은 응답의 **형식**을 안정적으로 만들 뿐, 분류·요약의 **내용이 사실인지**까지 보장하지는 않는다.

## 참고

- [Gemini API 실습](Gemini_API실습.md)
- [예외 처리](파이썬기초/14_예외처리.md) — `try`/`except`로 `ValidationError` 다루기
- [타입 힌트와 독스트링](파이썬기초/19_타입힌트와독스트링.md)
