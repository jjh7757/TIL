# Gemini 스트리밍 응답

일반 요청은 모델이 답변을 **전부 다 만든 뒤** 한 번에 돌려준다. 스트리밍은 만들어지는 대로 조각조각 바로 전달해서, 사용자가 응답을 기다리는 동안 화면이 멈춰 보이지 않고 실시간으로 텍스트가 채워지는 것처럼 보이게 한다.

## Generator로 원리 이해하기

[제너레이터](파이썬기초/20_추가문법모음.md#제너레이터--값을-미리-다-만들지-않고-하나씩)에서 본 `yield`가 스트리밍의 기본 원리와 같다 — 값을 한 번에 다 만들어 반환하는 대신, 준비되는 대로 하나씩 내보낸다.

```python
import time

def local_stream():
    chunks = "안녕하세요! 스트리밍 응답입니다."
    for chunk in chunks:
        time.sleep(0.5)   # 응답 조각이 늦게 도착하는 상황을 흉내
        yield chunk

for chunk in local_stream():
    print(chunk, end="", flush=True)   # 도착하는 즉시 출력
```

## SSE(Server-Sent Events)

SSE는 하나의 HTTP 연결을 계속 유지한 채로 서버가 클라이언트에 데이터를 계속 흘려보내는 방식이다. Gemini에 `stream=True`를 주면 SSE로 응답을 받고, `google-genai` SDK가 이를 Python 이벤트 객체로 변환해준다.

```python
event_stream = client.interactions.create(
    model=model,
    input="봄을 표현하는 긴 문장을 하나 작성해 줘.",
    stream=True,
    store=False,
)

for event in event_stream:
    print(event.event_type)   # 완성된 응답 하나가 아니라, 여러 이벤트가 순서대로 전달됨
```

## 텍스트 조각 실시간으로 출력하기

실제 응답 텍스트는 `step.delta`라는 이벤트 타입으로 조각 단위(delta)씩 전달된다. 텍스트 타입인 조각만 골라 바로 출력하면서 리스트에 모아둔다.

```python
text_parts = []

for event in stream:
    if event.event_type == "step.delta":
        delta = getattr(event, "delta", None)
        if getattr(delta, "type", None) == "text":
            text = getattr(delta, "text", "")
            if text:
                text_parts.append(text)
                print(text, end="", flush=True)   # 조각이 도착하는 즉시 화면에 출력

full_text = "".join(text_parts)   # 모든 조각을 이어붙이면 완성된 전체 응답
```

`getattr(obj, "속성", 기본값)`을 쓰는 이유는, 이벤트 종류마다 담긴 속성이 달라서 없는 속성에 바로 접근하면 에러가 날 수 있기 때문이다 — 없으면 `None`이나 빈 문자열을 기본값으로 받고 넘어간다.

## 왜 조각을 직접 모아야 하는가

[Gemini API 실습](Gemini_API실습.md)의 `interaction.output_text`는 응답이 전부 완성된 뒤에야 값이 채워지는 편의 속성이다. 스트리밍에서는 이 "완성된 결과"를 기다리지 않고 바로 보여주는 게 목적이므로, 조각(`delta`)들을 우리가 직접 순서대로 이어 붙여 필요할 때 전체 텍스트를 재구성한다.

## 참고

- [Gemini API 실습](Gemini_API실습.md)
- [추가 문법 모음](파이썬기초/20_추가문법모음.md) — 제너레이터
