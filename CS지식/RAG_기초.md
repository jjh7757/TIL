# RAG 기초 — 문서 처리와 임베딩

LLM은 학습 시점 이후의 정보나 비공개 문서(사내 규정, 최신 매뉴얼 등)를 모른다 — 알고 있는 것처럼 부정확하게 답할 수도 있다. **RAG(Retrieval-Augmented Generation)**는 질문과 관련된 문서를 먼저 **검색**한 뒤, 그 문서를 프롬프트에 넣어 **생성**하게 하는 방식이다. 모델을 재학습시키지 않고도 외부 문서를 답변 근거로 쓸 수 있지만, 검색된 문서가 부정확하면 답변도 부정확해진다.

```
❌ LLM만 사용 → "일반적으로 HR 부서에 문의하세요..." (모호함)
✅ RAG 사용  → 사내 규정 문서 검색 → "사내 포털 > 인사 > 연차 신청에서 가능합니다" (문서 근거)
```

## 전체 흐름

```
[ 인덱싱 단계 — 질문 전에 미리 수행 ]
문서 → 로드(Document Loader) → 분할(Text Splitter) → 임베딩 → 벡터 DB 저장

[ 질의 응답 단계 — 질문이 들어오면 수행 ]
질문 → 임베딩 → 벡터 DB 검색 → 관련 문서 추출 → LLM에 전달 → 응답 생성
```

## Document Loader — 문서 불러오기

| 로더 | 형식 |
|---|---|
| `TextLoader` | `.txt` |
| `PyPDFLoader` | `.pdf` (+ `pypdf` 필요) |
| `CSVLoader` | `.csv` |
| `WebBaseLoader` | 웹페이지 |

`load()`는 `Document` 객체의 리스트를 반환한다.

```python
Document(
    page_content="문서의 텍스트 내용...",   # 검색·임베딩에 쓰는 본문
    metadata={"source": "파일경로", "page": 0},  # 출처·페이지 등 부가 정보
)
```

로더마다 문서를 나누는 기준이 다르다 — `TextLoader`는 파일 전체를 하나의 `Document`로, `PyPDFLoader`는 **페이지 단위**로 나눈다(`page` metadata는 0부터 시작). 스캔 이미지 PDF는 OCR이 필요할 수 있고, 표·다단 편집 문서는 텍스트 순서가 뒤틀릴 수 있어 로더가 구조를 완벽히 복원하지 못할 때도 있다.

```python
loader = PyPDFLoader("data/report.pdf")
docs = loader.load()   # len(docs) == 페이지 수
```

## Text Splitter — 문서를 청크로 쪼개기

문서를 통째로 임베딩하면 두 가지 문제가 생긴다.

1. **검색 정확도 저하**: 긴 문서에 여러 주제가 섞이면 질문과 무관한 내용까지 함께 검색됨
2. **입력 크기 제한**: 임베딩 모델·LLM은 처리 가능한 토큰 수에 한계가 있음

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)
```

| 파라미터 | 의미 |
|---|---|
| `chunk_size` | 청크의 최대 크기(문자 수) |
| `chunk_overlap` | 인접 청크끼리 겹치는 부분 — 경계에서 문맥이 끊기는 것을 줄임 |

```
원본: [ABCDEFGHIJ], chunk_size=5, overlap=2
청크1: [ABCDE]  청크2: [DEFGH]  청크3: [GHIJ]
```

`RecursiveCharacterTextSplitter`는 `\n\n`(문단 경계) → `\n`(줄바꿈) → 공백 순으로 분할을 시도하는 범용 분할기다. 문서 특성에 따라 다른 분할기를 쓸 수도 있다.

| 방법 | 기준 | 적합한 상황 |
|---|---|---|
| `RecursiveCharacterTextSplitter` | 문자 수 | 범용 문서 |
| `TokenTextSplitter` | 토큰 수 | 임베딩 모델의 토큰 제한을 정확히 맞출 때 |
| `MarkdownHeaderTextSplitter` | 마크다운 헤더 | 섹션 구조를 유지하며 분할 |
| `SemanticChunker` | 인접 문장의 임베딩 유사도 | 주제 전환 기준 분할(계산량 증가) |

`chunk_size`는 문자 수 기준이지만 임베딩 모델의 입력 제한은 보통 토큰 수 기준이므로, 청크가 모델의 최대 입력을 넘지 않는지 별도로 확인해야 한다.

## 임베딩 — 텍스트를 벡터로

임베딩은 텍스트를 숫자 벡터로 바꾸는 것이다. **의미가 비슷한 텍스트는 비슷한 벡터**가 되므로, 벡터 간 거리로 의미적 유사도를 계산할 수 있다.

```
"고양이"  → [0.12, -0.34, ...] ─┐
"강아지"  → [0.11, -0.31, ...] ─┤ 가까움 (의미 유사)
"자동차"  → [-0.87, 0.42, ...] ─ 멂
```

벡터의 개별 숫자를 사람이 해석할 수는 없다 — 중요한 건 벡터 간 **상대적 거리**다. 문서와 질문을 비교하려면 반드시 **같은 임베딩 모델, 같은 차원 설정**으로 변환해야 한다.

```python
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2")

vector = embeddings.embed_query("고양이는 귀엽다")           # 검색 질문 — 문자열 하나 → 벡터 하나
vectors = embeddings.embed_documents(["문장1", "문장2"])    # 저장할 문서 — 문자열 리스트 → 벡터 리스트
```

`embed_query()`와 `embed_documents()`를 역할에 맞게 구분해 쓴다 — 질문 하나엔 전자, 저장할 문서 여러 개엔 후자.

## 코사인 유사도

두 벡터가 얼마나 비슷한 방향을 향하는지 측정한다. 범위는 -1~1이며 1에 가까울수록 유사하다.

```
cosine_similarity(A, B) = (A · B) / (|A| × |B|)
```

```python
def cosine_similarity(vec1, vec2):
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a**2 for a in vec1))
    magnitude2 = math.sqrt(sum(b**2 for b in vec2))
    return dot_product / (magnitude1 * magnitude2)
```

이 값은 벡터의 방향 관계일 뿐, 자연어의 "같은 의미"·"반대 의미"를 그대로 보장하지 않는다. 관련 여부를 가르는 보편적 기준 점수도 없다 — 점수 분포는 모델·데이터마다 달라서 검색 결과 비교나 평가 데이터로 기준을 직접 정해야 한다.

## 임베딩 기반 유사도 검색 (직접 구현 예시)

```python
documents = ["연차 신청은 그룹웨어의 근태 관리 메뉴에서 제출합니다.", "재택근무를 하려면...", ...]
document_vectors = embeddings.embed_documents(documents)

query = "휴가를 쓰려면 어디에서 신청하나요?"
query_vector = embeddings.embed_query(query)

scores = [(cosine_similarity(query_vector, dv), doc) for dv, doc in zip(document_vectors, documents)]
scores.sort(key=lambda item: item[0], reverse=True)   # 유사도 높은 순
top2 = scores[:2]
```

질문과 문서의 표현이 달라도("휴가" vs "연차") 의미가 비슷하면 찾아낸다는 게 키워드 매칭과의 핵심 차이다. 실무에서는 이 전수 비교를 직접 하지 않고 [벡터 DB](벡터DB.md)에 맡긴다.

## 참고

- [벡터 DB](벡터DB.md) — 임베딩을 저장·검색하는 전용 데이터베이스
- [Gemini 구조화 출력](Gemini_구조화출력.md) — 여기서도 쓰인 Pydantic 개념
