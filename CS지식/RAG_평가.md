# RAG 평가

[RAG 검색 고도화](RAG_검색고도화.md)에서 여러 검색 전략을 만들 수 있게 됐다면, 이제 "어떤 전략이 실제로 더 나은가"를 숫자로 답해야 한다. RAG 평가는 **검색이 정답 근거를 찾았는지**와 **그 근거로 만든 답변이 좋은지**를 분리해서 측정한다 — 둘을 섞어서 보면 답변이 나쁠 때 원인이 검색 실패인지 생성 실패인지 구분할 수 없다.

```
질문과 정답 문서
→ 검색기 실행 → Hit@k·Recall@k·MRR          (검색 평가 — LLM 호출 없음)
→ 답변 생성   → 인용 검사·RAGAS·LLM-as-Judge  (답변 평가 — LLM 호출)
```

## 평가 방법은 하나로 충분하지 않다

| 방법 | 특징 | 적합한 상황 |
|---|---|---|
| 수동 확인 | 대표 질문과 답변을 직접 읽음 | 초기 개발, 빠른 검증 |
| 검색 지표 | Hit@k, Precision@k, Recall@k, MRR | 검색 설정 비교, LLM 호출 없이 반복 실행 |
| RAGAS | LLM으로 답변의 근거성·관련성을 범용 평가 | 여러 파이프라인 설정 비교 |
| LLM-as-Judge | 도메인에 맞는 기준을 직접 정의 | 규정 답변처럼 정확성·완전성이 중요한 경우 |
| 사용자 피드백 | 실제 사용자의 반응 수집 | 서비스 운영 단계 |

질문이 몇 개 안 될 땐 수동 확인으로 충분하지만, 질문이 늘어나면 느리고 사람마다 판단이 갈린다. 그렇다고 자동 지표만 믿을 수도 없다 — 아래에서 보듯 RAGAS 점수가 높아도 검색된 문서 자체가 틀렸을 수 있다.

## 평가 데이터셋 — 4개 필드

평가는 질문·기대 정답·정답 문서를 사람이 미리 정리한 기준 데이터가 있어야 시작할 수 있다. 각 지표는 이 중 필요한 필드만 사용한다.

| 필드 | 설명 | 준비 방법 |
|---|---|---|
| `user_input` | 사용자 질문 | 직접 작성 |
| `reference` | 기대 정답 | 직접 작성 |
| `retrieved_contexts` | 검색된 문서 내용 | 검색기 실행 결과 |
| `response` | LLM이 생성한 답변 | RAG 파이프라인 실행 결과 |

검색 평가는 `user_input`과 정답 출처(`relevant_sources`)만으로 실행할 수 있어 LLM을 호출하지 않는다. 답변 평가는 여기에 `retrieved_contexts`·`response`를 더해야 한다.

질문 난이도는 easy·medium·hard를 섞어 구성한다. 쉬운 질문만 쓰면 점수가 지나치게 높게 나오고, 어려운 질문만 쓰면 "기본 검색이 안 되는 것"과 "여러 문서를 종합해야 하는 것"을 구분하기 어렵다.

## 검색 평가 — Hit@k, Precision@k, Recall@k, MRR

정답은 청크가 아니라 **정답이 담긴 문서(출처) 단위**로 정의한다. 검색기가 반환한 청크의 `source`가 정답 출처 목록에 포함되면 "정답을 찾았다"고 판단한다.

```python
# 상위 k개 안에 정답 출처가 하나라도 있으면 1
def hit_at_k(ranked, relevant, k):
    return int(bool(set(ranked[:k]) & set(relevant)))

# 상위 k개 중 정답 출처가 차지하는 비율
def precision_at_k(ranked, relevant, k):
    selected = ranked[:k]
    hits = sum(source in relevant for source in selected)
    return hits / len(selected) if selected else 0.0

# 전체 정답 출처 중 상위 k개에서 찾은 비율
def recall_at_k(ranked, relevant, k):
    hits = len(set(ranked[:k]) & set(relevant))
    return hits / len(set(relevant))

# 처음 등장한 정답 출처 순위의 역수 (여러 질문의 평균이 MRR)
def reciprocal_rank(ranked, relevant):
    relevant = set(relevant)
    for rank, source in enumerate(ranked, start=1):
        if source in relevant:
            return 1 / rank
    return 0.0
```

| 지표 | 답하는 질문 |
|---|---|
| Hit@k | 상위 k개 안에서 근거를 **하나라도** 찾았는가 |
| Precision@k | 상위 k개 중 관련 없는 청크가 얼마나 섞였는가 (낮으면 LLM에 불필요한 context가 많이 들어감) |
| Recall@k | 여러 문서를 종합해야 하는 질문에서 필요한 근거를 **빠짐없이** 가져왔는가 |
| MRR | 첫 근거가 상위 순위에 얼마나 빨리 나오는가 (k가 제한된 상황에서 특히 중요) |

같은 조건(같은 문서, 같은 `k`)에서 Similarity·MMR·BM25·Hybrid를 비교하면 전략 간 차이가 드러난다. 예를 들어 Hit@k와 MRR은 여러 전략에서 비슷하게 높아도, Precision@5는 MMR이 눈에 띄게 낮게 나올 수 있다 — MMR이 관련성보다 다양성을 우선하기 때문에 상위 5개 안에 관련 없는 문서가 섞여 들어간 결과다. 이런 차이는 전체 평균만 보면 가려지므로, 난이도별(easy/medium/hard)로 다시 나눠 집계하면 "여러 문서를 종합해야 하는 어려운 질문에서만 특정 전략이 약하다"처럼 더 구체적인 원인을 찾을 수 있다.

### 실패 사례를 직접 읽는다

`Recall@5 < 1`인 질문만 추려서 정답 출처와 실제 검색 결과를 나란히 보면, 어떤 규정이 반복해서 누락되는지 패턴이 보인다. 예를 들어 "혼인 시 지원"을 묻는 질문의 정답이 인사규정·경비처리규정·복리후생규정 세 개에 걸쳐 있는데, 검색 결과가 복리후생규정 한 곳에 쏠려 있다면 — 그 질문 자체가 여러 규정을 종합해야 하는 유형이거나, 청킹이 특정 규정 쪽에 편중되어 있다는 신호다. 지표 하나만으로는 "왜" 실패했는지 알 수 없고, 실패 사례를 읽어야 원인 가설을 세울 수 있다.

### File Hit vs Page Hit — 정답의 단위를 무엇으로 잡을지

정답을 "파일"로 정의할지 "파일 + 페이지"로 정의할지에 따라 같은 검색 결과도 다르게 평가된다.

```python
파일 일치: doc.metadata["source"] == case["target_file_name"]
페이지 일치: doc.metadata["page_no"] == case["target_page_no"]
정답 페이지: 파일 일치 and 페이지 일치
```

File Hit은 관련 파일을 찾았는지만 보고, Page Hit은 그 안에서 정답이 있는 정확한 페이지까지 찾았는지 본다. File Hit은 높은데 Page Hit이 낮다면, 청킹이나 검색 자체는 큰 틀에서 맞는 문서를 찾고 있지만 문서 내에서 정확한 위치를 짚어내지 못한다는 뜻이다 — 청크 크기를 줄이거나 `k`를 늘려야 할 신호로 읽을 수 있다. 정답 데이터를 준비할 때부터 어느 단위로 채점할지 미리 정해야 지표를 일관되게 해석할 수 있다.

## 답변 평가 — 규칙 기반 인용 검사부터

검색 평가를 통과했다고 답변이 안전한 건 아니다. 검색된 문서를 LLM에 전달해 답변을 만들 때, LLM이 답변과 함께 참고한 파일명(`citations`)을 구조화된 형태로 반환하게 하면 두 가지를 코드로 바로 검사할 수 있다.

```python
class GroundedAnswer(BaseModel):
    answer: str = Field(description="검색 근거로 작성한 답변")
    citations: list[str] = Field(description="답변에 사용한 규정 파일명")

# 인용 출처가 실제 검색된 문서에 포함되는가 (citations가 retrieved_sources의 부분집합인가)
valid_citation = bool(citations) and citations <= retrieved_sources
# 인용 출처 중 정답 문서가 하나라도 있는가
relevant_citation = bool(citations & set(relevant_sources))
```

이 검사는 같은 답변에 항상 같은 결과를 내는 결정적(deterministic) 검사라 반복 실행에 부담이 없다. 다만 "인용한 출처가 실제 검색 결과에 있는가"만 확인할 뿐, 문장 하나하나가 그 출처 내용과 실제로 일치하는지는 판단하지 못한다 — 이 의미적 품질은 RAGAS나 LLM-as-Judge가 담당한다.

## RAGAS — 범용 근거성·관련성 평가

RAGAS는 LLM과 임베딩을 이용해 답변의 의미를 평가하는 라이브러리다. 검색 지표가 "정답 문서를 찾았는가"만 보는 것과 달리, "그 문서로 실제로 좋은 답변을 만들었는가"까지 평가할 수 있다.

| 메트릭 | 사용하는 필드 | 확인하는 내용 |
|---|---|---|
| Faithfulness | `user_input`, `response`, `retrieved_contexts` | 답변의 주장이 검색 문서로 뒷받침되는가 |
| Answer Relevancy | `user_input`, `response` | 답변이 질문의 핵심과 관련되는가 |
| Context Precision | `user_input`, `reference`, `retrieved_contexts` | 정답 작성에 유용한 문서가 검색 결과 앞쪽에 있는가 |
| Context Recall | `user_input`, `reference`, `retrieved_contexts` | 기준 정답에 필요한 내용을 검색 문서가 빠짐없이 포함하는가 |
| Factual Correctness | `response`, `reference` | 답변의 사실이 기준 정답과 일치하는가 |
| Semantic Similarity | `response`, `reference` | 답변과 기준 정답의 의미가 유사한가 |

모든 메트릭을 다 쓸 필요는 없다 — Context Precision/Recall은 검색 지표(Hit@k, Recall@k)와 역할이 겹치므로, 검색은 자체 지표로 이미 평가했다면 답변 쪽은 Faithfulness와 Answer Relevancy만으로도 충분히 구분된다.

### Faithfulness — 근거 없는 주장을 잡아낸다

생성 답변을 검증 가능한 여러 주장으로 나눈 뒤, 각 주장이 `retrieved_contexts`로 뒷받침되는지 확인한다. 검색 문서에는 "재택근무는 주 2회 가능"이라고만 있는데 답변이 "팀장 승인 없이 주 2회 가능"이라고 하면, "주 2회 가능"은 근거가 있지만 "팀장 승인 없이"는 근거가 없어 점수가 낮아진다.

Faithfulness가 높다고 정답이라는 뜻은 아니다. 검색 문서 자체가 질문과 무관하거나 오래된 문서여도 답변이 그 문서에만 충실하면 높은 점수가 나올 수 있다 — 그래서 Faithfulness가 높은 문항도 검색 자체가 맞았는지는 Hit@k와 함께 확인해야 한다.

### Answer Relevancy — 질문의 핵심에 답했는가

답변만 보고 그 답변에 대응할 법한 질문을 여러 개 역으로 생성한 뒤, 생성한 질문들의 임베딩과 원래 질문의 임베딩 사이 평균 유사도로 점수를 계산한다. 이 지표는 `retrieved_contexts`나 `reference`와 사실을 대조하지 않으므로, 질문에 그럴듯하게 답했지만 내용이 틀린 답변도 높은 점수를 받을 수 있다.

### 두 점수를 함께 읽는다

| Faithfulness | Answer Relevancy | 해석 |
|---|---|---|
| 높음 | 높음 | 검색 근거로 질문에 직접 답함 |
| 높음 | 낮음 | 근거에는 충실하지만 질문의 핵심을 벗어남 |
| 낮음 | 높음 | 질문엔 직접 답했지만 근거 밖 내용을 지어냄 |
| 낮음 | 낮음 | 근거성도 관련성도 낮음 |

점수가 낮으면 `response`만 보지 말고 `user_input`·`retrieved_contexts`를 함께 확인한다 — 원인이 답변 생성이 아니라 앞 단계의 검색 실패일 수 있다. 한국어 표현·어미 차이와 평가 LLM이 만드는 역질문의 품질에 따라 점수가 흔들릴 수 있으므로, 절대 점수보다 같은 조건(같은 문항·모델·평가 설정)에서의 상대 비교에 집중한다. RAGAS 점수는 0~1 범위지만 모든 프로젝트에 통하는 절대 합격선은 없다.

## 직접 정의한 LLM-as-Judge — 도메인 기준이 필요할 때

RAGAS는 범용 근거성·관련성을 빠르게 평가하지만, "규정 문서의 수치·조건·예외를 정확히 인용했는가"처럼 도메인 특화 기준은 직접 정의해야 한다. "좋은 답변인가?"처럼 모호한 질문 대신, 수치·조건의 일치 여부, 누락 여부, 검색 근거 밖 주장 여부처럼 구체적인 채점 기준을 준다.

```python
class JudgeScore(BaseModel):
    correctness: int = Field(ge=1, le=10, description=(
        "기준 정답과 비교한 사실 정확성. 수치·조건·대상·예외가 틀리면 감점. "
        "대부분 틀리면 1점, 핵심은 맞지만 일부 오류면 5점, 모두 정확하면 10점."
    ))
    completeness: int = Field(ge=1, le=10, description="질문이 요구하는 핵심 내용을 빠짐없이 포함한 정도")
    groundedness: int = Field(ge=1, le=10, description="답변의 주장이 검색 문서로 뒷받침되는 정도")
    citation_accuracy: int = Field(ge=1, le=10, description="인용한 파일이 실제 답변 내용을 지지하는 올바른 출처인가")
    reason_of_correctness: str = Field(description="항목별 판단 근거와 감점 이유")
```

각 항목의 점수 기준(1점/5점/10점이 각각 어떤 상태인지)을 필드 설명에 명시해야 실행마다 채점 기준이 흔들리지 않는다. 평균 점수만 보지 말고 `reason` 필드로 왜 감점됐는지 함께 확인해야, 점수가 낮은 원인이 검색 문제인지 생성 문제인지 판단할 수 있다.

| 구분 | RAGAS | 직접 정의한 Judge |
|---|---|---|
| 장점 | 공통 메트릭을 바로 사용 가능 | 도메인 기준을 자유롭게 정의 |
| 주의점 | 평가 모델·언어에 따라 점수가 흔들림 | 채점 프롬프트와 기준 자체를 검증해야 함 |

## 평가 비용과 적용 시점

검색 지표(Hit@k, Precision@k, Recall@k, MRR)는 LLM을 호출하지 않고 정답 문서와 검색 순위만으로 계산하므로 반복 실행에 부담이 없다. 반면 답변 생성·RAGAS·LLM-as-Judge는 질문 수와 메트릭 수에 비례해 API 호출이 늘어난다. 그래서 개발 중에는 검색 평가를 자주 돌리고, 생성 평가는 난이도별 대표 문항부터, RAGAS·Judge는 필요한 메트릭만 선택해 실행하는 순서가 합리적이다.

| 시점 | 평가 방법 |
|---|---|
| 초기 개발 | 대표 질문을 직접 확인 |
| 검색 설정 변경 | Hit@k·Recall@k·MRR로 회귀 평가 |
| 프롬프트 변경 | RAGAS 또는 Judge로 답변 비교 |
| 문서 변경 | 관련 질문의 정답과 검색 결과 재검증 |
| 서비스 운영 | 사용자 피드백과 실패 질문 수집 |

평가 데이터셋은 한 번 만들고 끝나는 파일이 아니다. 실패한 질문을 발견하면 데이터셋에 추가하고, 문서 내용이 바뀌면 기대 정답과 정답 출처도 함께 갱신해야 평가가 계속 유효하다.

## 참고

- [RAG 검색 고도화](RAG_검색고도화.md) — 여기서 비교하는 Similarity/MMR/BM25/Hybrid 전략 자체
- [RAG 파이프라인](RAG_파이프라인.md) — 검색·생성·출처 표시를 체인으로 엮기
- [LangChain 구조화 출력](LangChain_구조화출력.md) — `with_structured_output()`으로 인용·채점 결과를 구조화하는 방법
