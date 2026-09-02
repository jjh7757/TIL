# 벡터 DB와 검색

[RAG 기초](RAG_기초.md)에서 텍스트를 임베딩 벡터로 바꾸는 법을 봤다. 이제 그 벡터들을 **저장**하고 **검색**해야 한다.

## 왜 일반 DB로는 부족한가

일반 DB(MySQL 등)는 정확한 일치(`WHERE name = '홍길동'`)나 범위 검색에 최적화되어 있다. 벡터 검색에 필요한 건 "이 벡터와 가장 비슷한 벡터 k개를 찾아줘"라는 **유사도 검색**이다. 벡터 10만 개를 질문이 올 때마다 하나하나 비교(`O(n)`)하면 데이터가 늘수록 선형으로 느려진다 — 벡터 DB는 이 문제를 풀기 위한 전용 데이터베이스다.

| | 일반 DB | 벡터 DB |
|---|---|---|
| 검색 방식 | 정확한 값 매칭(`=`, `>`, `<`) | 유사도 기반 근사 검색 |
| 인덱스 | B-Tree, Hash | HNSW, IVF 등 벡터 전용 인덱스 |
| 결과 | 조건에 맞는 정확한 결과 | "가장 비슷한" 근사 결과 |

RDB가 데이터를 **표**로 관리한다면, 벡터 DB는 데이터를 **지도**처럼 관리한다 — 각 데이터가 다차원 좌표 공간에서 위치를 점유하고, 그 **위치가 곧 의미**이며 **검색은 거리를 재는 것**이다.

## ANN(Approximate Nearest Neighbor) — 근사 최근접 이웃

전수 비교(Exact Search) 대신 인덱스로 후보를 빠르게 좁혀서 검색 속도를 높이는 방식. 항상 정확히 같은 결과를 보장하진 않지만(재현율은 데이터·설정에 따라 달라짐) 대규모 벡터에서 훨씬 빠르다.

| 알고리즘 | 원리 | 특징 |
|---|---|---|
| **HNSW** | 가까운 벡터들을 간선으로 연결한 다층 그래프 탐색 | 속도·재현율 우수, 추가 메모리 필요. Chroma의 기본 인덱스 |
| **IVF** | 벡터 공간을 클러스터로 나누고 가까운 일부만 검색 | 압축 기법(PQ)과 결합 가능, FAISS가 대표적으로 지원 |

실무에서 ANN 내부를 직접 구현할 일은 없다 — 중요한 건 "왜 빠른지"의 원리를 아는 것이다.

## 저장/검색 흐름과 메타데이터

```
[저장] 문서 → 청킹 → 임베딩 → 벡터 + 메타데이터 → 벡터 DB 저장(인덱스 구축)
[검색] 질문 → 임베딩 → 벡터 DB에서 ANN 검색 → 상위 k개 문서 반환
```

저장할 때 벡터뿐 아니라 **원본 텍스트**와 **메타데이터**(출처, 페이지 등)도 함께 넣는다 — 검색 결과로 벡터가 아니라 원본 텍스트를 받아야 LLM에 전달할 수 있기 때문이다.

| 구성 요소 | 설명 |
|---|---|
| 벡터 | 임베딩 모델이 만든 좌표값. 유사도 검색에 사용 |
| 원본 텍스트 | 벡터의 원래 내용. LLM에 전달할 때 사용 |
| 메타데이터 | 필터링·문서 식별·출처 표시용 구조화 정보 |

**메타데이터는 임베딩되지 않는다.** 좌표에 점을 찍고 포스트잇을 붙여두는 것과 같다 — 유사도 검색 대상이 아니라 결과를 **필터링**하는 데 쓴다.

```
1. 메타데이터로 대상 제한: "user_id가 'kim'인 데이터만" ← 정확한 매칭(RDB처럼)
2. 그중에서 질문과 가장 가까운 k개 반환         ← 유사도 기반
```

멀티테넌트(사용자별 문서 필터링), 문서 구분(여러 PDF 중 특정 문서만 검색), 페이지 범위 제한 등에 쓰인다. `PyPDFLoader` 같은 로더는 `source`/`page`를 자동으로 채워준다. **메타데이터 내용으로 의미 검색까지 하고 싶다면, 그 내용을 원본 텍스트에 포함시켜 함께 임베딩해야 한다** — 메타데이터 자체는 검색 대상이 아니기 때문이다.

## 벡터 DB 비교

| 도구 | 특징 | 적합한 상황 |
|---|---|---|
| **Chroma** | 임베디드·서버·클라우드 지원, 로컬 저장 간단 | 학습, 프로토타입, 소규모 RAG |
| **pgvector** | PostgreSQL 확장, 관계형 데이터와 함께 관리 | 기존 PostgreSQL 기반 서비스 |
| **FAISS** | Meta의 검색·클러스터링 라이브러리, CPU/GPU 지원 | 원문·메타데이터 DB 기능은 별도 구성 필요 |
| **Pinecone** | 완전 관리형 클라우드 벡터 DB | 운영 환경의 확장성·관리 편의 우선 |

## Chroma 실습

```python
import chromadb
from langchain_chroma import Chroma

COLLECTION_NAME = "spri_ai_brief"   # RDB의 테이블에 해당
PERSIST_DIR = "./chroma_db"         # RDB의 데이터베이스 파일에 해당

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    collection_name=COLLECTION_NAME,
    persist_directory=PERSIST_DIR,   # 지정하면 로컬 디스크에 자동 저장됨(.persist() 호출 불필요)
)
```

### 유사도 검색

```python
results = vectorstore.similarity_search("즈푸 AI의 AI 모델 이름이 뭐야?", k=3)

# 특정 페이지만 대상으로 — 메타데이터 필터링
results = vectorstore.similarity_search(query, k=3, filter={"page": 6})

# 유사도 점수와 함께
results = vectorstore.similarity_search_with_score(query, k=3)
```

> Chroma 기본 설정에서 `similarity_search_with_score`는 **유클리드 거리(L2)**를 반환한다 — **값이 작을수록 유사**하다(코사인 유사도와 방향이 반대이니 주의).

### 기존 벡터 스토어에 다시 연결하기

이미 저장된 데이터가 있으면 재임베딩 없이 생성자로 바로 연결한다.

```python
existing_store = Chroma(
    embedding_function=embeddings,
    collection_name=COLLECTION_NAME,
    persist_directory=PERSIST_DIR,
)
existing_store.similarity_search("구글의 AI 관련 소식은?", k=3)
```

> ⚠️ **임베딩 모델을 바꾸면 벡터 DB를 재구축해야 한다.** 모델이 다르면 벡터의 차원·좌표 공간이 달라 기존 벡터와 섞어 쓸 수 없다. "검색 품질이 갑자기 나빠졌다"의 흔한 원인이 임베딩 모델 불일치이므로, 어떤 모델로 저장했는지 반드시 기록해둔다.

### Retriever — 체인에 연결하기 위한 표준 인터페이스

체인에서는 `Retriever.invoke(질문) → 문서 리스트`라는 통일된 인터페이스를 기대한다. `as_retriever()`로 벡터 스토어를 변환한다.

```python
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
docs = retriever.invoke("AI 투자 규모는 어느 정도야?")
```

이 `retriever`를 [LangChain 기초](LangChain_기초.md)의 `RunnablePassthrough.assign(context=...)`에 연결하면, 질문만 넘겨도 관련 문서가 자동으로 context에 채워지는 RAG 체인을 만들 수 있다.

## 참고

- [RAG 기초](RAG_기초.md)
- [LangChain 기초](LangChain_기초.md) — Runnable, RunnablePassthrough
