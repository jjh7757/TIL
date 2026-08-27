# Gemini 멀티모달 입력

지금까지는 텍스트만 주고받았지만, Gemini에는 이미지·PDF·음성·동영상도 텍스트와 함께 전달할 수 있다.

## 파일을 전달하는 세 가지 방법

| 방법 | 전달 값 | 적합한 상황 |
|---|---|---|
| Base64 | `data` | 작고 한 번만 쓰는 파일 |
| Files API | `uri` | 크거나 여러 요청에서 재사용할 파일 |
| 공개 URL | `uri` | 인터넷에서 바로 접근 가능한 파일 |

## Base64로 직접 전달하기 — 작은 파일

파일을 읽어 Base64 문자열로 바꿔서 `data`에 넣는다. [Gemini API 실습](Gemini_API실습.md)에서 본 Content 배열 형태에 `type: "image"`를 추가하는 것뿐이다.

```python
import base64
from pathlib import Path

image_path = Path("sample.jpg")
mime_type = "image/jpeg"
image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")

interaction = client.interactions.create(
    model=model,
    input=[
        {"type": "image", "data": image_data, "mime_type": mime_type},
        {"type": "text", "text": "이 이미지에 무엇이 보이는지 설명해 줘."},
    ],
    store=False,
)
print(interaction.output_text)
```

## Files API로 전달하기 — 크거나 재사용할 파일

파일을 먼저 업로드해서 URI를 발급받고, 이후 요청에서는 이 URI만 참조한다. **업로드와 모델 요청은 별개의 작업**이라, 업로드한 파일 하나를 여러 질문에서 재사용할 수 있다.

```python
uploaded_file = client.files.upload(file="sample.jpg")

interaction = client.interactions.create(
    model=model,
    input=[
        {"type": "image", "uri": uploaded_file.uri, "mime_type": uploaded_file.mime_type},
        {"type": "text", "text": "이 이미지에 무엇이 보이는지 설명해 줘."},
    ],
    store=False,
)
```

Files API의 업로드 방식은 파일 종류(이미지/PDF/음성/동영상)와 무관하게 동일하다 — 달라지는 건 `input`에 넣는 `type` 하나뿐이다.

```python
def input_type_from_mime(mime_type: str) -> str:
    if mime_type.startswith("image/"): return "image"
    if mime_type.startswith("audio/"): return "audio"
    if mime_type.startswith("video/"): return "video"
    return "document"   # PDF 등

uploaded = client.files.upload(file="sample.pdf")
input_type = input_type_from_mime(uploaded.mime_type)   # "document"
```

`client.files.get(name=...)`으로 업로드한 파일의 URI, MIME type, 처리 상태를 다시 확인할 수 있다.

## 이미지 생성하기

이미지 생성 모델에 장면을 설명하면 결과를 Base64 이미지로 돌려준다.

```python
image_model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")

image_interaction = client.interactions.create(
    model=image_model,
    input="따뜻한 오후 햇살이 비치는 책상 위의 노트북과 커피잔을 수채화 스타일로 그려 줘.",
    response_format={"type": "image", "mime_type": "image/jpeg", "aspect_ratio": "16:9"},
)

Path("generated_image.jpg").write_bytes(
    base64.b64decode(image_interaction.output_image.data)
)
```

`response_format`으로 응답 형식을 강제한다는 점은 [Gemini 구조화 출력](Gemini_구조화출력.md)에서 JSON 구조를 강제하던 것과 같은 개념이다 — 여기서는 텍스트가 아니라 이미지로 응답 형식을 지정한다.

## 참고

- [Gemini API 실습](Gemini_API실습.md) — Content 배열 형태
- [Gemini 구조화 출력](Gemini_구조화출력.md) — `response_format`으로 응답 형식 강제
