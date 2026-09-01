# LangSmith 기초

LangSmith는 LangChain 애플리케이션의 실행 과정을 기록하고 분석하는 관측성(observability) 플랫폼이다. 체인이 정확히 뭘 했는지 — 어떤 프롬프트가 만들어졌고, 모델이 뭘 반환했고, 어디서 얼마나 걸렸는지 — 를 눈으로 확인할 수 있다.

```bash
pip install langsmith
```

## 환경변수만 설정하면 자동으로 기록된다

```
GEMINI_API_KEY=...
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=langchain-gemini-prac
```

[환경변수 관리](환경변수관리.md)에서 본 대로 `.env`에 넣고 `load_dotenv()`로 로드하면, 별도의 콜백 코드를 작성하지 않아도 **Runnable을 실행하는 순간 자동으로** LangSmith에 트레이스가 기록된다.

```python
chain = prompt | llm | StrOutputParser()
result = chain.invoke({"question": "Python 데코레이터가 뭐야?"})
# 이 한 줄만으로 LangSmith 프로젝트에 실행 기록이 남는다
```

## 태그와 메타데이터로 실행 구분하기

`config`로 실행 목적이나 실험 버전을 남겨두면 LangSmith 화면에서 쉽게 필터링할 수 있다.

```python
result = chain.invoke(
    {"question": "리스트와 튜플의 차이는 뭐야?"},
    config={
        "run_name": "python-basic-question",
        "tags": ["gemini", "basic", "class-demo"],
        "metadata": {"lesson": "01-1", "model_family": "gemini"},
    },
)
```

## LangSmith 화면에서 확인할 것

- 체인의 실행 순서 (프롬프트 → 모델 → 출력 파서)
- 템플릿 변수가 실제로 적용된 최종 프롬프트
- 입력·출력 토큰 수와 각 단계의 소요 시간
- 지정한 `run_name`, 태그, 메타데이터
- 실패한 실행이 있다면 어느 단계에서 오류가 났는지

## 선택적 추적

전체 실행을 항상 기록하지 않고 특정 구간만 추적하고 싶으면 `tracing_context`를 쓴다.

```python
import langsmith as ls

with ls.tracing_context(enabled=True, project_name="langchain-gemini-selective"):
    result = chain.invoke({"question": "Python 제너레이터가 뭐야?"})
```

## 참고

- [LangChain 기초](LangChain_기초.md)
- [환경변수와 .env 관리](환경변수관리.md)
