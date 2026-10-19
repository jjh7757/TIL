# 로컬 LLM — Ollama와 Hugging Face

API 대신 **내 PC에서 LLM을 직접 실행**하는 방법. [LangChain 기초](LangChain_기초.md)의 체인(`prompt | llm | parser`)에서 **모델 부분만 바꾸면** 나머지는 그대로 동작한다.

## Ollama

로컬에서 LLM을 쉽게 실행하게 해주는 도구. `ollama pull`로 모델을 받고 `ollama run`으로 실행한다.

- Llama(Meta), Qwen(Alibaba), Gemma(Google) 등 다양한 오픈소스 모델 지원
- **로컬 API 서버를 띄워주기 때문에** LangChain 같은 외부 도구에서 쉽게 연동된다
- **양자화(quantization)**: 모델 가중치를 낮은 정밀도로 표현해 크기와 메모리 사용량을 줄이는 기법. Ollama에서는 이미 양자화된 모델을 받아 실행한다.

### 설치와 실행

```bash
ollama serve                  # 서버 실행 (Ollama 앱이 이미 켜져 있으면 생략)
ollama pull qwen3.5:0.8b      # 새 터미널에서 모델 다운로드
pip install langchain-ollama
```

- 서버를 띄운 터미널은 열어 두고, **다운로드는 새 터미널**에서 한다.
- 노트북 실습 중에도 Ollama 서버는 실행 상태로 유지해야 한다.
- 모델명의 `0.8b`는 파라미터가 약 8억 개라는 뜻 (`B` = billion, 10억). 파라미터는 모델이 학습 과정에서 조정하는 내부 수치.

### LangChain 연결 — 모델만 교체

```python
from langchain_ollama import ChatOllama

local_llm = ChatOllama(model="qwen3.5:0.8b", reasoning=False)   # 모델만 교체

chain = prompt | local_llm | parser     # 나머지는 Gemini 때와 동일
```

`reasoning=False`는 추론(thinking) 출력을 끄는 옵션이다. 작은 모델에서 응답이 길어지는 걸 막는다.

Gemini 쪽은 `ChatGoogleGenerativeAI(model=...)` + `.env`의 `GOOGLE_API_KEY`, Ollama 쪽은 API 키 없이 로컬 서버가 대상이다. LangChain의 ChatModel 인터페이스가 같기 때문에 체인 코드는 바뀌지 않는다.

## Hugging Face — 모델의 GitHub

오픈소스 AI 모델의 **GitHub 같은 플랫폼**. LLM뿐 아니라 이미지·음성 모델도 공유된다.

| 메뉴 | 내용 |
|---|---|
| Models | 수십만 개의 사전학습 모델을 검색·다운로드 |
| Datasets | 학습용 데이터셋 공유·다운로드 |
| Spaces | 모델을 웹에서 바로 체험하는 데모 공간 |

Ollama 라이브러리에 없는 모델도 Hugging Face에서 **GGUF 형식**으로 받으면 Ollama로 실행할 수 있다. 이렇게 모델을 모아놓은 플랫폼을 **Model Hub**라고 부른다.

## 로컬 모델 vs Gemini API

| 비교 항목 | 로컬 LLM (qwen3.5:0.8b) | Gemini API (gemini-3.6-flash) |
|---|---|---|
| 비용 | API 호출 비용 없음, 장비·전력 필요 | 요금제와 사용량에 따라 달라짐 |
| 인터넷 | 모델 다운로드 후 로컬 추론에는 불필요 | 필요 |
| 사용 한계 | PC 메모리와 연산 성능 | 요청 수·토큰 수 등 API 호출 한도 |

"로컬 = 공짜"는 아니다. 비용이 API 요금에서 장비·전력·성능 제약으로 옮겨갈 뿐이고, 0.8b 같은 작은 모델은 품질이 API 모델보다 떨어질 수 있다. 외부로 보내면 안 되는 데이터나 오프라인 환경, 비용 고정이 필요한 경우에 선택지가 된다.

## 한 줄 정리

- Ollama = 로컬 LLM 실행기 + 로컬 API 서버. `ChatOllama`로 모델만 바꿔 끼우면 기존 체인이 그대로 돈다.
- Hugging Face = 모델 허브. GGUF로 받으면 Ollama에서 실행 가능.
- 양자화로 크기·메모리를 줄이고, `0.8b`는 파라미터 8억 개.
