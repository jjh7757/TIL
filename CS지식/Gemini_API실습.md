# Gemini API로 LLM 호출하기

Google의 Gemini 모델에 Python 코드로 요청을 보내고 응답을 사용하는 기본 흐름 정리.

```bash
pip install google-genai
```

[환경변수 관리](환경변수관리.md)에서 다룬 대로 API 키는 코드에 직접 적지 않고 `.env`에 넣어 로드한다.

```python
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError(".env 파일에 GEMINI_API_KEY를 설정해 주세요.")

model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
client = genai.Client(api_key=api_key)
```

## REST 요청과 SDK의 관계

SDK 없이 [requests](requests실습.md)로 직접 호출해보면, `client.interactions.create(...)`가 실제로는 URL·headers(`x-goog-api-key`)·body(JSON)로 이루어진 평범한 HTTP POST 요청을 감싼 것임을 알 수 있다. SDK는 이 요청 조립과, 응답 JSON에서 최종 텍스트를 꺼내는 과정(`output_text`)을 대신해줄 뿐이다.

```python
response = client.interactions.create(
    model=model,
    input="LLM API를 30자 이내의 한 문장으로 설명해줘.",
    store=False,
)
print(response.output_text)
```

`Interaction` 객체는 딕셔너리가 아니라 점(`.`)으로 접근한다 — `response.id`(요청 고유 ID), `response.status`, `response.steps`(입력·출력 과정), `response.output_text`(최종 텍스트).

## `input`에 넣을 수 있는 형태

| 형태 | 용도 |
|---|---|
| 문자열 | 한 번의 간단한 질문 |
| Content 배열 | 한 요청에 텍스트·이미지 등 여러 내용을 함께 전달 |
| Step 배열 | 대화 이력(누가 무엇을 말했는지)을 직접 구성 |

```python
# Content 배열 — 하나의 user_input Step 안에 여러 Content
client.interactions.create(
    model=model,
    input=[
        {"type": "text", "text": "다음 단어를 한 문장으로 묶어 줘."},
        {"type": "text", "text": "사과, 바나나, 과일 바구니"},
    ],
    store=False,
)
```

`user_input`은 대화의 **단계(Step)**이고, 그 안의 `text`/`image` 등은 단계에 담기는 **내용(Content)**이다 — 문자열 입력은 이 구조의 축약형일 뿐이다.

## `system_instruction` — 답변 전반의 역할/규칙

`system_instruction`은 매 요청에 적용되는 역할·톤·제약을, `input`은 이번에 처리할 실제 질문을 담는다.

```python
result = client.interactions.create(
    model=model,
    input="API 키를 코드에 직접 적으면 왜 위험해? 한 문장으로 답해줘.",
    system_instruction="보안 담당자입니다. 단호한 말투로 40자 이내에서 답하세요.",
    store=False,
)
```

## 대화 맥락 이어가기

기본적으로 각 요청은 서로 독립적이다 — 이전 요청에서 이름을 말해도, 다음 요청에 그 내용을 넣지 않으면 모델은 기억하지 못한다.

**방법 1 — 수동 history**: 이전 Step들을 모아 매번 다시 보낸다.

```python
history = [{"type": "user_input", "content": [{"type": "text", "text": "내 이름은 민수야."}]}]
turn1 = client.interactions.create(model=model, input=history, store=False)

# 모델 응답 Step을 dictionary로 변환해 history에 이어붙인다
history.extend(step.model_dump(exclude_none=True) for step in turn1.steps)
history.append({"type": "user_input", "content": [{"type": "text", "text": "내 이름이 뭐야?"}]})

turn2 = client.interactions.create(model=model, input=history, store=False)
```

**방법 2 — `store=True` + `previous_interaction_id`**: 서버가 대화를 저장하고, 다음 요청에 이전 interaction의 ID만 넘기면 이어진다. 대화 기록 전체를 매번 다시 보낼 필요가 없다.

```python
turn1 = client.interactions.create(model=model, input="내 이름은 민수야.", store=True)
turn2 = client.interactions.create(
    model=model,
    input="내 이름이 뭐야?",
    previous_interaction_id=turn1.id,
    store=True,
)
```

`previous_interaction_id`에는 가장 최근 ID만 넣을 수 있는 게 아니다 — 이전의 특정 ID를 다시 지정하면 그 시점에서 **새로운 대화로 분기**할 수 있다(그 이후에 진행된 다른 대화가 삭제되는 것은 아니다). 대화가 길어질수록 토큰·비용·지연 시간이 늘어난다는 점도 고려해야 한다.

## `generation_config` — 생성 방식 제어

프롬프트가 "무엇을 답할지"를 설명한다면, `generation_config`는 "어떻게 생성할지"를 코드로 설정한다.

```python
client.interactions.create(
    model=model,
    input="LLM API를 한 문장으로 설명해줘.",
    generation_config={
        "max_output_tokens": 1000,   # 생성 가능한 최대 토큰 수 (글자 수는 아님)
        "thinking_level": "high",    # low/medium/high — 답변 전 추론 수준
    },
    store=False,
)
```

## 에러 처리 — 실패도 정상적인 흐름

Google GenAI SDK는 400번대를 `ClientError`, 500번대를 `ServerError`로 구분한다. [예외 처리](파이썬기초/14_예외처리.md)에서처럼, 원인별로 나눠 처리해야 무엇을 고칠지 알 수 있다.

```python
from google.genai import errors

def ask_gemini(prompt: str) -> str | None:
    try:
        result = client.interactions.create(model=model, input=prompt, store=False)
        return result.output_text
    except errors.ClientError as error:
        if error.code in (401, 403):
            print("인증 실패: API 키와 권한을 확인하세요.")
        elif error.code == 429:
            print("사용량 제한에 도달했습니다. 잠시 후 다시 요청하세요.")
        else:
            print(f"요청 오류({error.code}): {error.message}")
        return None
    except errors.ServerError as error:
        print(f"서버 오류({error.code}): 잠시 후 다시 요청하세요.")
        return None
```

| 오류 | 예 | 대응 |
|---|---|---|
| `ClientError` | 잘못된 API 키·모델명·요청 형식 | 요청/설정 수정 |
| `ClientError` 429 | 사용량 제한 | 잠시 후 재시도 |
| `ServerError` | 서버 일시 장애(500번대) | 잠시 후 재시도 |

## 참고

- [환경변수와 .env 관리](환경변수관리.md)
- [requests로 API 호출하기](requests실습.md)
- [예외 처리](파이썬기초/14_예외처리.md)
- [Gemini 구조화 출력](Gemini_구조화출력.md)
