# RAG 파이프라인 — 체인으로 엮기

[RAG 기초](RAG_기초.md)와 [벡터 DB](벡터DB.md)의 조각들(문서 로드·청킹·임베딩·저장·검색)을 실제로 **하나의 실행 흐름**으로 엮는 방법.

```
인덱싱 단계: 문서 로드 → 청킹 → 임베딩 → 벡터 DB 저장
질의 단계:   질문 임베딩 → 유사 문서 검색 → context 구성 → 프롬프트 입력 → LLM 답변 생성
```

## 1. 먼저 단계별로 손으로 실행해보기

```python
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

prompt = ChatPromptTemplate.from_messages([
    ("system", "아래 검색된 문서를 참고하여 질문에 답변해줘. "
               "검색 결과에 없는 내용은 \"해당 정보를 찾을 수 없습니다\"라고 답변해.\n\n[검색된 문서]\n{context}"),
    ("human", "{question}"),
])

docs = retriever.invoke(question)          # 1. 검색
context = format_docs(docs)                 # 2. 포매팅
answer = (prompt | llm | StrOutputParser()).invoke({"context": context, "question": question})  # 3. 생성
```

## 2. `RunnablePassthrough.assign()`으로 하나의 체인으로 압축

[LangChain 기초](LangChain_기초.md)에서 본 패턴 그대로 — 호출자는 `question`만 넘기면, 체인 내부가 검색·포매팅을 알아서 처리해 `context`를 채워 넣는다.

```python
def retrieve_context(inputs):
    docs = retriever.invoke(inputs["question"])
    return format_docs(docs)

rag_chain = (
    RunnablePassthrough.assign(context=retrieve_context)
    | prompt | llm | StrOutputParser()
)

rag_chain.invoke({"question": "오픈AI의 차세대 모델에 대해 설명해줘"})
```

## 3. 딕셔너리로 병렬 입력을 구성하는 대안 문법

```python
rag_chain_parallel = (
    {
        "context": retriever | format_docs,     # retriever의 출력을 format_docs로 바로 이어받음
        "question": RunnablePassthrough(),        # 원본 입력을 그대로 통과
    }
    | prompt | llm | StrOutputParser()
)

rag_chain_parallel.invoke("오픈AI의 차세대 모델에 대해 설명해줘")   # 문자열 하나만 넘기면 됨
```

`2`와 `3`은 같은 결과를 만드는 두 문법이다. `assign()`은 "기존 입력 딕셔너리를 유지하며 새 키 추가", 딕셔너리 방식은 "각 키마다 독립적인 처리 경로를 지정" — 입력이 이미 딕셔너리 형태로 여러 값을 담고 있으면 `assign()`이, 단일 값 하나만 받는 게 자연스러우면 딕셔너리 병렬 구성이 더 간결하다.

### 왜 굳이 체인으로 조합하는가

| 구분 | 단계를 직접 호출 | LCEL 파이프라인 |
|---|---|---|
| 실행 방식 | 각 단계 결과를 변수로 전달 | 여러 단계를 하나의 chain으로 조합 |
| 중간 값 확인 | 변수로 바로 확인하기 쉬움 | 반환 구조를 별도로 구성해야 함 |
| 비동기·스트리밍 | 각 단계에서 직접 구현 | `chain.stream()`/`ainvoke()` 등 공통 인터페이스 적용 |
| LangSmith 추적 | 호출이 별도 trace로 기록될 수 있음 | 하나의 trace에서 전체 흐름 확인 |

둘 중 하나만 써야 하는 건 아니다. 검색 결과를 검사하거나 조건 분기가 필요한 부분은 함수로 작성하고, 전체 실행 흐름은 LCEL로 조합하는 식으로 섞어 쓸 수 있다.

## 출처(Citation) 표시하기

답변이 어떤 문서에 근거하는지 보여주면 사용자가 근거를 확인하고 할루시네이션을 점검하는 데 도움이 된다.

| 방식 | 설명 | 예 |
|---|---|---|
| Inline Citation | 답변 문장 끝에 `[1]`, `[2]` 삽입 | 학술 논문 스타일 |
| Source List | 답변 하단에 참조 문서 목록 별도 표시 | Perplexity AI 스타일 |

```python
citation_prompt = ChatPromptTemplate.from_messages([
    ("system", "아래 검색된 문서를 참고하여 답변해줘.\n"
               "1. 답변의 각 문장 끝에 출처 번호를 [1], [2] 형태로 표시해\n"
               "2. 검색 결과에 없는 내용은 절대 만들어내지 마\n\n[검색된 문서]\n{context}"),
    ("human", "{question}"),
])

def format_docs_with_index(docs):
    return "\n\n".join(f"[{i+1}] (페이지 {doc.metadata.get('page', '?')}) {doc.page_content}"
                        for i, doc in enumerate(docs))

def citation_rag(question: str):
    docs = retriever.invoke(question)          # retriever를 한 번만 호출해 재사용
    context = format_docs_with_index(docs)
    answer = (citation_prompt | llm | StrOutputParser()).invoke({"context": context, "question": question})
    return answer, docs   # 답변과 원본 문서를 함께 반환해야 출처를 화면에 보여줄 수 있다
```

> ⚠️ 출처 번호도 LLM이 생성한 결과라 정확성이 자동으로 보장되지 않는다. 모델이 잘못된 번호를 붙이거나, 인용한 문서가 답변을 충분히 뒷받침하지 못할 수 있으므로 실제 문서 내용과 함께 확인해야 한다.

## 참고

- [RAG 기초](RAG_기초.md)
- [벡터 DB](벡터DB.md)
- [RAG 검색 고도화](RAG_검색고도화.md)
- [LangChain 기초](LangChain_기초.md) — `RunnablePassthrough`, LCEL
- [RAG 평가](RAG_평가.md) — 이 체인이 만든 답변을 인용 검사·RAGAS·LLM-as-Judge로 평가하기
