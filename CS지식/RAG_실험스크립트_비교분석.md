# RAG 실험 스크립트 — 내 구현 vs 참고 구현 비교

같은 과제(`RAG_EXPERIMENT_GUIDE.ipynb` + `CONFIG_INPUT_OUTPUT_GUIDE.md`)를 두 사람이 각각 스크립트로 구현한 결과를 비교했다. 내 구현은 [RAG 실험 스크립트](RAG_실험스크립트.md)에 정리해둔 것이고, 참고 구현은 이후 저장소에 올라온 예시 코드다.

비교 목적은 "누가 더 잘했나"가 아니라 **과제가 요구한 input/output 항목을 각자 어디까지 충족했고, 놓친 항목이 결론에 어떤 영향을 줬는지** 확인하는 것이다. 실제로 놓친 항목 하나가 내 결론을 바꿀 만한 측정 비대칭을 만들고 있었다.

## 한눈에 보기

| | 내 구현 | 참고 구현 |
|---|---|---|
| 진입점 | `app.py`, `compare.py` (2개) | `main.py`, `show.py`, `generate.py`, `evaluate_generation.py` (4개) |
| 모듈 | `rag_experiment/` 패키지 8개 | 평면 모듈 7개 |
| 파이프라인 | **한 프로세스에서 검색→생성까지** | **단계별로 분리**, 저장된 결과를 다음 단계가 재사용 |
| 결과 저장 | `summary.json` 1개 (집계 중심) | JSONL 5종 + JSON 4종 (문항별 원자료 보존) |
| 생성 평가 | 규칙 기반 인용 검사 2지표 | RAGAS 3지표(faithfulness/relevancy/correctness) |
| 프롬프트 | 코드에 하드코딩 | `prompts/*.txt` 외부 파일 |
| config 검증 | 검색 전략 오타만 | 전 항목 `validate_config()` |
| RPM 대응 | 재시도 + **쿼리 캐싱 + 페이싱** | 재시도만 |
| 실제 돌린 실험 | 8개 조건 (+스윕 결론 문서) | 2개 조건 |

큰 그림은 **내 쪽은 "많은 조건을 빠르게 돌리는 것"에, 참고 구현은 "한 조건을 깊게 들여다보는 것"에 최적화돼 있다.** 그래서 내 쪽은 스윕을 8개까지 돌렸지만 왜 그런 결과가 나왔는지 사후에 볼 수 없고, 참고 구현은 조건 2개만 돌렸지만 문항별로 실패 원인을 추적할 수 있다.

## input 목록 비교

과제 문서(`CONFIG_INPUT_OUTPUT_GUIDE.md`)가 "input으로 받으면 좋은 것"으로 제시한 15개 항목을 기준으로 대조했다.

| 과제가 제시한 input | 내 구현 | 참고 구현 |
|---|---|---|
| 문서 경로 | `document.data_dir` (+`pattern`) | `data.documents_dir` |
| 평가 데이터 경로 | `golden_set_path` | `data.evaluation_path` |
| `chunk_size` | `chunking.chunk_size` + **CLI** | `chunking.chunk_size` |
| `chunk_overlap` | `chunking.chunk_overlap` + **CLI** | `chunking.chunk_overlap` |
| 임베딩 모델 | `embedding_model` | `embedding.model` |
| 검색 전략 | `retrieval.strategies` + **CLI** | `retrieval.strategies` |
| `k` | `retrieval.k` + **CLI** | `retrieval.k` |
| `fetch_k` | △ `mmr_fetch_k` — **MMR에만 적용** | `retrieval.fetch_k` — MMR·Hybrid·BM25 공통 |
| `lambda_mult` | ✗ 없음 (LangChain 기본값 고정) | `retrieval.lambda_mult` |
| `weights` | `retrieval.hybrid_weights` | `retrieval.weights` |
| `context_k` | ✗ 없음 (`retrieval.k` 재사용) | `generation.context_k` |
| 프롬프트 경로 | ✗ 없음 (코드에 하드코딩) | `generation.prompt_path` |
| 생성 모델 | `generation.llm_model` | `generation.model` |
| 평가 모델 | ✗ 없음 (LLM 평가 없음) | `evaluation.model` |
| 생성 평가 지표 | ✗ 없음 (규칙 기반 고정) | `evaluation.ragas_metrics` |

**충족률: 내 구현 9.5/15, 참고 구현 15/15.**

각자 체크리스트에 없는 항목을 추가한 것도 있다.

| 내 구현만 있는 input | 참고 구현만 있는 input |
|---|---|
| `document.pattern` (PDF 외 확장자 대응) | `name`, `description` (실험 식별·설명) |
| `metrics.k_values` (Hit@k의 k 목록을 설정으로) | `chunking.strategy` (분할 방식 확장 여지) |
| `generation.enabled` (생성 단계 on/off) | `chunking.separators` (분할 기준 문자) |
| `generation.case_limit` (생성 문항 수 제한) | `chunking.include_source` (청크 본문에 파일명 삽입) |
| `generation.pace_seconds` (API 호출 간격) | `output_dir` (결과 루트) |

**CLI 표면은 내 쪽이 넓다.** 내 구현은 `--chunk-size`/`--chunk-overlap`/`--strategies`/`--k`로 config를 수정하지 않고 조건을 덮어쓸 수 있어서, config 파일 하나로 k 스윕과 weights 스윕을 돌릴 수 있었다. 참고 구현은 조건마다 config 파일을 새로 만들어야 한다(그래서 `configs/`에 3개뿐이다). 실제로 내가 8개 조건을 돌릴 수 있었던 건 이 설계 덕이다.

반대로 **참고 구현에만 있는 CLI가 두 개 있고 둘 다 쓸모가 크다.**

- `--dry-run`: PDF 로드와 청킹까지만 하고 문서 수·문항 수·검색 설정을 출력한 뒤 멈춘다. API를 호출하지 않고 저장도 하지 않으니, 경로 오타를 임베딩 쿼터를 태우기 **전에** 잡을 수 있다.
- `--limit N`: golden set 앞쪽 N문항만 쓴다. **모든 단계에 적용된다.** 내 `--case-limit`은 생성 단계에만 적용되고 검색은 항상 35문항 전체를 돌기 때문에, 검색 쪽에는 빠른 확인 경로가 아예 없었다. 429를 여러 번 겪으면서도 "일단 5문항만 돌려보기"를 못 한 이유가 이거였다.

## output 목록 비교

과제 문서가 제시한 output 범주 6개로 대조했다.

| 과제가 제시한 output | 내 구현 | 참고 구현 |
|---|---|---|
| 사용한 input | `summary.json.config` (최종 config 전체) | `run.json` — config + **Python·패키지 버전 + 입력 파일 SHA-256** |
| 검색 결과 (문항별) | ✗ **저장 안 함** | `retrieval.jsonl` — 문항별 전략·순위·파일명·페이지·**청크 본문**·검색시간·적중여부 |
| 검색 평가 결과 (집계) | `summary.json.results` + `comparison.csv` | `retrieval_metrics.json` + `show.py` 표 출력 |
| 좋아진/나빠진 질문 사례 | ✗ 없음 | `comparisons/*/cases.jsonl` — 문항별 MRR 델타 + `improved`/`degraded`/`same` |
| Hit@k 미적중 문항 | ✗ 없음 | `retrieval_misses.jsonl` — 실패한 지표 종류 + 정답 위치 + 실제 검색 문서 |
| 생성 결과 | `summary.json.generation.answers` — 답변·인용·검색된 파일명 | `generation.jsonl` — + **검색 문맥 본문**·생성 시간 |
| 생성 평가 결과 | `generation.summary` — 규칙 기반 2지표 | `generation_evaluation.jsonl`(문항별) + `generation_metrics.json`(집계) |

파일 구조로 보면 이렇게 갈린다.

```
[내 구현]                          [참고 구현]
outputs/                           outputs/
├─ <실험>/summary.json  ← 전부      ├─ <실험>/
├─ comparison.csv                  │  ├─ chunks.jsonl          검색에 쓴 모든 청크
└─ sweep_findings.md   ← 수동 작성  │  ├─ retrieval.jsonl       문항별 검색 결과
                                   │  ├─ retrieval_misses.jsonl 미적중 문항만
                                   │  ├─ retrieval_metrics.json 전략별 집계
                                   │  ├─ run.json              재현 정보(+해시)
                                   │  ├─ generation.jsonl       문항별 생성 답변
                                   │  ├─ generation_summary.json
                                   │  ├─ generation_evaluation.jsonl
                                   │  └─ generation_metrics.json
                                   └─ comparisons/<A-vs-B>/
                                      ├─ summary.json          지표 델타
                                      └─ cases.jsonl           문항별 변화
```

과제 문서는 이 점을 명시적으로 요구하고 있었다 — **"평균 점수만 제공하지 않고 질문별 검색 결과를 함께 제공해야 검색에 성공하거나 실패한 이유를 확인할 수 있다."** 내 구현이 정확히 이걸 놓쳤다.

그런데 놓친 방식이 특이하다. 내 `evaluation.py`는 문항별 행(`rows`)을 **이미 다 계산하고 있다.** 지표 계산에 쓴 뒤 `summarize()`로 평균만 내고, `reporting.py`가 그 평균만 저장한다. 즉 데이터가 없어서 못 한 게 아니라 **계산해놓고 버렸다.** 저장 함수 하나만 추가하면 됐던 일이다. 집계를 저장하는 코드를 먼저 쓰고 나면 원자료가 이미 손에 있다는 걸 잊게 된다.

JSONL을 쓴 이유도 분명하다. 한 줄에 JSON 객체 하나라서 대용량 결과도 문항 단위로 스트리밍해 읽을 수 있고, 실패 문항만 필터링하기 쉽다. 내 `summary.json`은 생성 답변까지 한 파일에 넣어서 `with-generation` 결과가 12KB인데, 문항 수를 35개로 늘리면 통째로 파싱해야 하는 단일 JSON이 계속 커진다.

## 결론에 영향을 준 차이: Hybrid의 MRR이 과대평가되고 있었다

가장 중요한 발견이다. 참고 구현은 **모든 전략의 반환 개수를 k로 강제**한다.

```python
# 참고 구현 — 네 전략 모두 정확히 k개
searches["bm25"]       = lambda q: bm25.invoke(q)[:k]        # fetch_k개 받아서 k개로 자름
searches["similarity"] = lambda q: vectorstore.similarity_search(q, k=k)
searches["mmr"]        = lambda q: vectorstore.max_marginal_relevance_search(q, k=k, ...)
searches["hybrid"]     = lambda q: hybrid.invoke(q)[:k]      # ← 이 슬라이스가 핵심
```

내 구현은 `EnsembleRetriever`의 반환값을 자르지 않고 그대로 평가에 넘겼다. `EnsembleRetriever.weighted_reciprocal_rank()`는 **하위 검색기들의 고유 문서를 전부 정렬해 반환하고 k로 자르지 않는다.** 하위 검색기 두 개에 각각 `k=5`를 줬으니 Hybrid는 최대 10개를 반환한다. 직접 확인해봤다.

```
각 하위 검색기 반환: 5개, 5개
EnsembleRetriever(id_key 없음) → 10개 반환, 순위: [0, 5, 1, 6, 2, 7, 3, 8, 4, 9]
[:5] 슬라이스 후             →  5개 반환, 순위: [0, 5, 1, 6, 2]
```

여기서 내 `reciprocal_rank()`가 문제가 된다. 이 함수는 `docs[:k]`로 자르지 않고 **받은 리스트 전체를 훑는다.**

```python
def reciprocal_rank(docs, case):
    for rank, doc in enumerate(docs, start=1):   # 슬라이스 없음
        if 파일·페이지 일치:
            return 1 / rank
    return 0.0
```

결과적으로 **MRR의 탐색 깊이가 전략마다 달랐다** — Similarity/MMR/BM25는 5위까지만 볼 수 있었고, Hybrid만 최대 10위까지 볼 수 있었다. 6~10위에서 정답을 찾은 문항은 Hybrid만 점수를 얻는다. 구조적으로 Hybrid에 유리한 측정이다.

크기를 따져보면 무시할 수 없다. 35문항에서 한 문항이 6~10위에 걸리면 MRR에 `(1/6 ~ 1/10) / 35 ≈ 0.003~0.005`가 더해진다. 내가 관측한 Hybrid의 MRR 우위는 baseline에서 **0.9095 vs 0.9071 = 0.0024**, k 스윕 전체에서도 0.002~0.005 수준이었다. **우위 폭이 이 편향의 크기와 같은 자리수다.** 그러니 "Hybrid가 1위"라는 결론은 이 데이터로 지지되지 않는다.

다만 **Hit@k 계열은 오염되지 않았다.** `file_hit_at_k`/`page_hit_at_k`는 `docs[:k]`로 자르고 들어가므로 네 전략 모두 각자의 상위 k개를 비교하는 공정한 측정이다. 그래서 baseline에서 Hybrid의 `page_hit@3`가 0.943으로 나머지 0.914보다 높았던 건 **실제 우위**로 봐도 된다. 즉 정정 후 남는 결론은 "Hybrid는 상위 3개 안에 정답 페이지를 넣는 비율이 더 높다"이고, MRR 순위 비교는 다시 측정해야 한다.

교훈은 이렇다. **여러 후보를 비교할 때는 지표 계산 코드보다 "각 후보가 같은 조건으로 입력을 받았는지"를 먼저 확인해야 한다.** 지표 함수는 셋 다 정확하게 구현돼 있었다. 틀린 건 비교 조건이었고, 그건 지표를 아무리 검산해도 안 나온다.

### 곁가지: Hybrid의 융합 후보 수도 달랐다

같은 곳에서 차이가 하나 더 나온다. RRF는 여러 검색 결과를 순위 기반으로 합치는 방식이라 **후보 풀이 깊을수록 유리하다.**

| | 내 구현 | 참고 구현 |
|---|---|---|
| 벡터 검색이 Hybrid에 넘기는 후보 | `k=5` | `fetch_k=20` |
| BM25가 Hybrid에 넘기는 후보 | `k=5` | `fetch_k=20` |
| 융합 후 최종 반환 | 자르지 않음 (~10개) | `[:5]` |

내 Hybrid는 5+5를 합쳤고 참고 구현은 20+20을 합쳤다. 같은 `hybrid_weights=0.5/0.5`라도 융합 대상이 다르니 사실 다른 실험이었다. 내가 "`hybrid_weights`를 0.3/0.7~0.7/0.3으로 바꿔도 MRR 차이가 0.005 이하"라고 결론냈는데, 후보 풀이 5+5로 얕아서 가중치를 바꿀 여지 자체가 작았을 가능성이 있다. 가중치의 영향을 제대로 보려면 `fetch_k`를 키우고 다시 재봐야 한다.

`EnsembleRetriever(id_key="chunk_id")`도 참고 구현에만 있다. `id_key`가 없으면 `page_content`로 중복을 판정하는데, 참고 구현은 청킹 단계에서 `chunk_id = f"{source}:{index}"`를 붙여 그걸 기준으로 삼는다. 본문이 우연히 같은 청크가 생기면(표지·목차·반복 양식이 많은 공공문서에서 충분히 가능하다) 내 쪽은 서로 다른 청크를 하나로 합쳐버린다.

## 내 구현이 앞선 부분

### RPM 대응은 내 쪽이 한 단계 더 갔다

참고 구현의 API 보호는 **재시도(지수 백오프 8회)뿐이다.** `main.py`가 `embeddings.client`에 재시도 클라이언트를 붙이는 게 전부이고, 쿼리 임베딩 캐싱이나 호출 간격 강제는 없다. 재시도 파라미터(`attempts=8, initial_delay=2.0, max_delay=60.0, exp_base=2, jitter=1.0`)는 내 것과 완전히 동일하다.

내 구현은 여기에 `RateLimitedEmbeddings`로 두 겹을 더 얹었다 — 같은 질문 텍스트 캐싱, 문서 임베딩 배치별 최소 간격 강제. 분당 요청이 5회 안팎이라는 걸 실측한 뒤 필요해서 넣은 것이고, 덕분에 `--limit` 없이 35문항 × 4전략 전체를 끝까지 돌릴 수 있었다. 참고 구현의 README가 `--limit 5`부터 시작하라고 안내하고 429가 계속되면 "`--limit`을 줄이거나 할당량이 갱신된 뒤 다시 실행"하라고 적어둔 건, 이 부분을 사용자 운영으로 넘겼다는 뜻이다.

**다만 이건 트레이드오프였다.** 캐싱 때문에 내 `latency_ms`는 전략 비교에 못 쓰게 됐다([RAG 실험 스크립트](RAG_실험스크립트.md)에 정리). 참고 구현은 캐싱이 없으니 `avg_latency_ms`가 모든 전략에서 실제 end-to-end 시간이고, README도 "알고리즘 자체의 순수 연산 속도보다 현재 파이프라인의 end-to-end 응답 시간으로 해석한다"고 정확히 범위를 좁혀 적어뒀다. **처리량을 사서 측정 가능성을 팔았다**는 게 정확한 요약이다.

### 스윕 범위와 결론 문서

실제로 돌린 실험은 내 쪽이 8개(baseline, chunk-550, chunk-small, k-3, k-10, hybrid weights 2종, with-generation), 참고 구현이 2개(chunk-500, chunk-700)다. `comparison.csv`로 전 실험을 한 표에 모으고 `sweep_findings.md`에 결론과 남은 작업까지 적어둔 것도 내 쪽에만 있다.

`compare.py`와 `--compare`는 목적이 다르다.

| | 내 `compare.py` | 참고 구현 `main.py --compare` |
|---|---|---|
| 대상 | `outputs/` 아래 **모든** 실험 | **두 개** 실험(baseline vs candidate) |
| 출력 | 집계 지표 한 표 + CSV | 지표 델타 + 문항별 변화 + improved/degraded 개수 |
| 강한 질문 | "8개 조건 중 뭐가 제일 나은가" | "이 조건을 바꿨을 때 어느 문항이 어떻게 변했나" |

둘 다 필요한 도구고, 스윕을 넓게 돌리려면 내 쪽 형태가 편하다. 참고 구현은 비교 전에 두 결과의 `strategy`와 `query_id` 집합이 같은지 검사해서 다르면 예외를 던지는데(다른 golden set이나 다른 `--limit`으로 돌린 결과를 섞지 못하게), 이건 내 쪽에 없는 안전장치다.

## 설계 철학의 차이

### 단일 프로세스 vs 단계 분리

내 `app.py`는 문서 로드→청킹→검색→평가→생성을 한 번에 실행한다. 참고 구현은 `main.py`(검색·평가) → `generate.py`(생성) → `evaluate_generation.py`(RAGAS)로 쪼개고, 각 단계가 앞 단계의 **저장된 결과 파일**을 읽는다.

단계를 쪼갠 이득이 구체적이다.

- **검색을 다시 돌리지 않는다.** `generate.py`는 `retrieval.jsonl`의 `documents`를 그대로 문맥으로 쓴다. 내 `generate_answer()`는 `retriever.invoke()`를 다시 호출하므로, 평가한 검색 결과와 생성에 쓴 검색 결과가 원리적으로 별개다(같은 값이 나오더라도 보장은 없다).
- **프롬프트만 바꿔 재실험할 수 있다.** 검색을 다시 안 돌리니 임베딩 API 비용이 0이다. 내 구조에서는 프롬프트를 바꾸려면 전체 파이프라인을 다시 돌려야 한다.
- **실패 지점이 좁다.** RAGAS 평가에서 터져도 검색 결과와 생성 답변은 이미 디스크에 있다.

대신 단계가 늘어나 실행 명령이 4개가 되고, 중간 파일 스키마를 지켜야 한다는 부담이 생긴다. 참고 구현이 `generation.jsonl`이 없으면 "`generate.py`를 먼저 실행하라"는 안내를 README 문제 해결 절에 넣어둔 게 그 부담의 표현이다.

### 생성 평가: 규칙 기반 vs RAGAS

| | 내 구현 | 참고 구현 |
|---|---|---|
| 방식 | 규칙 기반 인용 검사 | RAGAS (LLM 심판) |
| 지표 | `valid_citation`, `relevant_citation` | `faithfulness`, `answer_relevancy`, `answer_correctness` |
| `target_answer` 사용 | ✗ **안 씀** | `answer_correctness`의 기준 답변 |
| 비용 | 0 (문자열 비교) | 평가 LLM + 임베딩 API 추가 호출 |
| 5문항 실행 결과 | 두 전략 모두 1.0 / 1.0 (**포화**) | — |

내 쪽 지표는 공짜이고 결정적(deterministic)이지만, 앞서 확인한 대로 5문항에서 전부 1.0이 나와 변별력이 없었다. 더 근본적으로 **golden set의 `target_answer` 필드를 아예 쓰지 않았다.** 인용한 파일명이 맞는지만 보고 답변 내용이 기준 답변과 맞는지는 측정하지 않았으니, 애초에 "정답성"을 잴 수 없는 설계였다. 참고 구현의 `answer_correctness`가 정확히 그 자리를 메운다.

반대로 RAGAS는 호출 비용이 붙고 LLM 심판이라 재현성이 떨어진다. 규칙 기반 검사를 1차 게이트로 두고 통과한 것만 RAGAS로 채점하는 조합이 실용적일 것 같다.

### 재현성

참고 구현의 `run.json`은 실행 시각과 config에 더해 **Python 버전, 추적 패키지 버전 5종, golden set의 SHA-256, 모든 입력 PDF의 파일명+SHA-256**을 남긴다. 두 결과가 정말 같은 데이터로 나왔는지 해시로 확인할 수 있다. 내 `summary.json`은 config와 timestamp만 남기므로, PDF가 중간에 교체됐어도 알 방법이 없다.

`case_id`도 같은 목적이다. 참고 구현은 golden set에 `case_id`가 없으면 `sha256(question + file + page)[:12]`로 안정적인 ID를 만들어 붙인다. 문항 순서가 바뀌어도 같은 문항은 같은 ID를 갖기 때문에 실행 간 문항별 조인이 가능하다. 내 구현에는 문항 ID가 없어서, 문항별 비교를 하려면 질문 문자열로 맞춰야 한다.

### 실패를 빨리 드러내기

참고 구현의 `validate_config()`는 config를 읽는 즉시 전 항목을 검사하고 한국어 메시지로 던진다 — 필수 섹션 누락, `0 <= chunk_overlap < chunk_size`, `fetch_k >= k`, `0 <= lambda_mult <= 1`, `weights` 2개·음수 불가·합 0 불가, 프롬프트 파일 존재, `generation.strategies ⊆ retrieval.strategies`, 허용된 RAGAS 지표. `main()`도 예외를 stderr로 찍고 종료 코드를 구분한다(`KeyboardInterrupt` → 130).

내 구현은 `build_retrievers()`에서 검색 전략 오타만 검사한다. `chunk_overlap`이 `chunk_size`보다 커도, 프롬프트가 잘못돼도 그냥 진행한다. 임베딩 API를 태우고 몇 분 뒤에 터지는 것과 시작 0초에 터지는 것의 차이는 무료 티어 쿼터를 쓰는 상황에서 특히 크다. `--dry-run`이 이 사고방식의 연장이다.

## 참고 구현을 읽을 때 주의할 점

참고 구현의 README와 실제 코드가 몇 군데 어긋난다. 참고 자료를 읽을 때 README를 그대로 믿으면 안 된다는 사례로 남긴다.

- README의 프로젝트 구성에 `test_experiment.py`가 있고 `python -m pytest rag_experiment_example/test_experiment.py -q` 실행법까지 안내하지만, **저장소에 그 파일이 없다.**
- README는 디렉터리를 `rag_experiment_example/`로, `.env` 위치를 `langchain_gemini`로 안내하지만, 실제 경로는 `langchain_/10-rag-evalution-script/`이고 `.env`는 `config.py`의 `ROOT_DIR`(= `langchain_/`) 기준이다.
- `configs/chunk-1000.json`은 있지만 `outputs/`에는 `chunk-500`과 `chunk-700`만 있다. 청크 1000 조건은 참고 구현에서도 실행 결과가 없다 — 내 쪽이 API 쿼터로 못 돌린 그 조건이다.

## 정리: 다음에 반영할 것

우선순위대로.

1. **Hybrid 반환값을 `[:k]`로 자른다.** 측정 비대칭이 결론을 바꿀 수 있는 문제라 가장 급하다. 고친 뒤 MRR 순위 비교를 다시 해야 한다.
2. **문항별 결과를 저장한다.** 이미 계산하고 있는 `rows`를 `retrieval.jsonl`로 쓰고, Hit@k 미적중 문항을 따로 모은다. 스윕 해석의 근거가 여기서 나온다.
3. **`--limit`과 `--dry-run`을 추가한다.** 검색 단계에도 빠른 확인 경로를 만든다.
4. **`fetch_k`를 Hybrid의 하위 검색기에도 적용한다.** 그 후에 `hybrid_weights` 스윕을 다시 본다.
5. **`validate_config()`를 넣는다.** 최소한 `chunk_overlap < chunk_size`, `fetch_k >= k`.
6. **프롬프트를 외부 파일로 빼고 `target_answer`를 쓰는 정답성 지표를 넣는다.** 현재 규칙 기반 검사만으로는 답변 품질을 측정하지 못한다.
7. **`run.json` 수준의 재현 정보와 `case_id`를 남긴다.**

가장 크게 배운 건 3번이나 5번 같은 편의 기능이 아니라 1번이다. **지표를 정확히 구현하는 것과 비교를 공정하게 설계하는 것은 다른 일이고, 후자는 지표를 검산해서는 발견되지 않는다.** 내 지표 함수 세 개는 참고 구현과 사실상 동일하게 맞게 구현돼 있었는데도 결론이 흔들린 이유가 그것이다.

## 참고

- [RAG 실험 스크립트](RAG_실험스크립트.md) — 내 구현의 설계와 스윕 결과 (이 문서에서 정정한 MRR 결론 포함)
- [RAG 평가](RAG_평가.md) — Hit@k/MRR 정의, RAGAS와 LLM-as-Judge, 인용 규칙 검사
- [RAG 검색 고도화](RAG_검색고도화.md) — MMR의 `fetch_k`/`lambda_mult`, BM25와 형태소 분석, EnsembleRetriever의 RRF
