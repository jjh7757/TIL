# LangChain Structured Output과 Output Parser

Gemini 응답을 문자열이 아니라 리스트·JSON(dict)·Pydantic 객체로 받는 방법들과, 그중 무엇을 언제 쓸지 정리.

## Output Parser 종류

| 방법 | 결과 타입 | 사용 시점 |
|---|---|---|
| `StrOutputParser` | `str` | 일반 텍스트만 필요할 때 |
| `CommaSeparatedListOutputParser` | `list[str]` | 단순 문자열 목록 |
| `JsonOutputParser` | `dict`/`list` | 유연한 JSON 데이터 |
| `PydanticOutputParser` | Pydantic 객체 | JSON 파싱 + 스키마 검증 |
| `with_structured_output()` | Pydantic 객체 등 | 모델의 네이티브 구조화 출력 사용 |

**핵심 차이**: parser 방식(`get_format_instructions()`)은 모델에게 형식을 **강제**하지 않고 자연어 지시로 **유도**할 뿐이다. 모델이 설명을 덧붙이거나 필드를 빠뜨릴 수 있다. `with_structured_output()`은 스키마를 모델 API에 직접 전달해 더 간결하고 안정적이지만, 값이 업무적으로 올바르다는 것까지 보장하진 않는다.

```
프롬프트 + get_format_instructions() → 형식을 "안내"
Output Parser                        → 실제 응답을 변환·형식 위반 검출
with_structured_output()             → 스키마를 모델 API에 직접 전달
```

## 구조화 출력의 4단계 검증

JSON으로 변환됐다고 곧바로 애플리케이션에서 쓸 수 있는 올바른 데이터라는 뜻은 아니다.

```
JSON 문법 검증 → schema 검증 → domain 규칙 검증 → policy 검증
```

| 단계 | 확인 내용 | 실패 예 |
|---|---|---|
| JSON 문법 | 올바른 JSON인가 | 따옴표·중괄호 누락 |
| Schema | 필드·타입이 맞는가 | 필수 필드 누락 |
| Domain | 업무 범위에 맞는 값인가 | 감정 강도가 1~5 범위를 벗어남 |
| Policy | 서비스 정책상 허용되는가 | 근거 없이 위험한 판단을 확정 |

Output Parser와 Pydantic은 앞의 두 단계(JSON 문법, Schema)만 검증한다. Domain·Policy는 별도 validator와 애플리케이션 로직으로 확인해야 한다.

## `PromptTemplate.partial()` — 고정값 미리 채워두기

Python의 `functools.partial()`처럼, 매번 바뀌지 않는 값을 미리 바인딩해 새 템플릿을 만든다.

```python
prompt = PromptTemplate.from_template("입력: {text}\n{format_instructions}")
prompt = prompt.partial(format_instructions=parser.get_format_instructions())

prompt.invoke({"text": "분석할 문장"})   # format_instructions는 이미 채워져 있으므로 text만 넘기면 됨
```

`format_instructions`는 parser가 정한 고정 규칙, `text`는 호출마다 달라지는 입력이다. `.partial()`은 즉시 완성된 문자열을 만들거나 LLM을 호출하지 않고, **남은 변수만 받는 새 템플릿**을 반환한다.

## 파서별 사용 예

```python
# 쉼표 구분 목록 — 태그·키워드 같은 단순 1차원 목록에 적합. 구조가 복잡해지면 JsonOutputParser로
list_parser = CommaSeparatedListOutputParser()
list_prompt = PromptTemplate.from_template(
    "{topic}과 관련된 핵심 키워드 5개를 작성해 주세요.\n{format_instructions}"
).partial(format_instructions=list_parser.get_format_instructions())

# 고정 스키마까지는 필요 없고 dict만 필요할 때
json_parser = JsonOutputParser()

# JSON 파싱 + Pydantic 검증 — 필수 필드, 타입, 값 범위까지 적용
class SentimentResult(BaseModel):
    sentiment: Literal["긍정", "부정", "중립"] = Field(description="문장에서 나타나는 감정")
    intensity: int = Field(ge=1, le=5, description="감정 강도")
    reason: str = Field(min_length=1, description="판단 근거")

pydantic_parser = PydanticOutputParser(pydantic_object=SentimentResult)
```

`sentiment: str`처럼 필드 설명만으로는 실제 허용값을 제한하지 못한다 — `"만족"`, `"모름"` 같은 값도 문자열이라 통과해버린다. `Literal["긍정", "부정", "중립"]`처럼 **타입 자체로 허용값을 명시**해야 Pydantic이 검증 단계에서 걸러낸다. 숫자는 `ge`/`le`, 문자열은 `min_length`처럼 데이터 특성에 맞는 제약을 추가한다.

## `with_structured_output()` vs `PydanticOutputParser`

```python
structured_llm = llm.with_structured_output(SentimentResult)
result = structured_llm.invoke("배송은 빨랐지만 포장이 찢어져 있어서 아쉬웠습니다.")
```

| 구분 | `with_structured_output()` | `PydanticOutputParser` |
|---|---|---|
| 구조 전달 방식 | 스키마를 모델 API에 전달 | format instructions를 프롬프트에 전달 |
| 모델 요구사항 | 해당 모델의 구조화 출력 지원 필요 | 일반 텍스트 출력 모델에서도 사용 가능 |
| 검증 시점 | 모델 호출 과정과 결합 | 문자열 응답을 받은 뒤 파싱·검증 |
| 제어 범위 | 간결하지만 provider 동작에 의존 | 전처리·예외 처리·재시도를 직접 구성 가능 |

모델이 네이티브 구조화 출력을 안정적으로 지원하면 `with_structured_output()`을 우선 고려한다. 다만 지원하지 않는 provider를 쓸 때, 여러 provider에서 같은 프롬프트/파싱 방식을 유지해야 할 때, 이미 저장된 JSON 문자열을 검증해야 할 때, 파싱 실패를 세밀하게 제어해야 할 때는 `PydanticOutputParser`가 더 적합하다.

## 실패했을 때 — 원인을 구분해야 대응이 정확해진다

실패는 세 층위 중 하나에서 일어난다.

- **Provider/API 실패**: 모델이 구조화 출력을 지원하지 않거나 요청 자체가 실패 — 원본 응답이 없어 예외 발생
- **파싱 실패**: 응답은 왔지만 JSON 문법·구조가 잘못됨
- **검증 실패**: JSON은 맞지만 타입·필수 필드·범위 조건 위반

```python
diagnostic_llm = llm.with_structured_output(SentimentResult, include_raw=True)
result = diagnostic_llm.invoke("생각보다 나쁘지는 않았지만 다시 구매할지는 모르겠습니다.")

result["parsed"]         # 검증된 객체 (성공 시)
result["parsing_error"]  # 실패 원인 (실패 시)
result["raw"]            # 원본 응답
```

> ⚠️ `include_raw=True`일 때 실패는 **예외가 아니라 `parsing_error` 값**으로 돌아온다. `.with_retry()`/`.with_fallbacks()`는 **예외가 발생해야** 동작하므로, 진단용 결과를 그대로 재시도/fallback 체인에 연결하면 자동 복구가 실행되지 않는다. 진단 모드와 운영 복구 체인은 분리한다.

### 재시도

`.with_retry()`는 같은 문자열에 parser만 다시 적용하는 게 아니라, **체인 전체를 다시 실행**해 모델로부터 새 응답을 받는다.

```python
retry_demo_chain = (
    RunnableLambda(count_attempts) | pydantic_prompt | fake_retry_llm | pydantic_parser
).with_retry(
    retry_if_exception_type=(OutputParserException,),   # 재시도할 예외 종류 제한
    stop_after_attempt=3,                                 # 무한 반복 방지
)
```

### Fallback

primary 체인에서 예외가 밖으로 전달될 때만 fallback이 같은 입력으로 다음 체인을 실행한다. 정상 값을 반환하면 fallback은 아예 실행되지 않는다.

```python
resilient_chain = primary_chain.with_fallbacks([fallback_chain])
```

실제 운영에서는 primary에 `llm.with_structured_output(Schema)`를, fallback에는 parser 기반 체인이나 다른 모델을 연결한다. 인증 오류나 정책 위반처럼 전환해도 해결되지 않는 오류까지 무조건 fallback하지 않도록 대상 예외를 구분해야 한다.

### 모든 실패를 재시도하면 안 된다

| 실패 상황 | 권장 처리 |
|---|---|
| JSON 형식이 일시적으로 잘못됨 | 횟수를 제한해 재시도 |
| 필수 입력이 부족함 | 사용자에게 추가 정보 요청 |
| 허용 범위를 벗어난 값 | 오류를 알리고 중단하거나 재입력 |
| 정책상 허용되지 않는 결과 | 재시도하지 않고 중단 |
| 일시적인 provider 장애 | 조건에 따라 fallback |

## 선택 기준 정리

- 단순 텍스트 → `StrOutputParser`
- 유연한 JSON → `JsonOutputParser`
- 프롬프트 기반 JSON + 엄격한 검증 → `PydanticOutputParser`
- 모델이 지원하고 스키마가 명확 → `with_structured_output()`

운영 환경에서는 파싱·검증 실패에 대비해 `chain.with_retry(stop_after_attempt=3)` 같은 예외 처리를 항상 함께 구성한다.

## 참고

- [LangChain 기초](LangChain_기초.md)
- [Gemini 구조화 출력](Gemini_구조화출력.md) — 같은 문제를 Gemini SDK 방식으로 다룰 때
- [예외 처리](파이썬기초/14_예외처리.md)
- [RAG 평가](RAG_평가.md) — `with_structured_output()`으로 인용·LLM-as-Judge 채점 결과를 구조화하는 예
