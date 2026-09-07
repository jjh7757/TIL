# RAG 실험 스크립트

[RAG 평가](RAG_평가.md)에서 Hit@k·MRR 같은 지표를 정의했다면, 이제 그 지표로 "여러 조건을 실제로 반복 비교"할 수 있는 구조가 필요하다. 노트북에 청크 크기나 검색 전략을 하드코딩해두면 조건 하나 바꿀 때마다 코드를 고쳐야 한다. **조건은 config 파일로, 실행 시점 값은 CLI로** 분리하면 같은 코드로 여러 실험을 돌리고 결과를 보존할 수 있다.

```
config.json (문서 경로·청킹·검색·평가 설정)
  + CLI 인자 (--config, --result-dir, --experiment-name, --chunk-size 등으로 일부 덮어쓰기)
  → app.py 실행 → outputs/<experiment-name>/summary.json 저장
  → compare.py로 여러 summary.json을 표/CSV로 비교
```

## config와 CLI 인자는 역할이 다르다

config는 "이 실험의 조건이 무엇인지"를 코드 밖에 남겨 재현 가능하게 하는 것이고, CLI 인자는 "지금 이 실행에서 무엇을 바꿔볼지"를 빠르게 지정하는 것이다. 둘을 헷갈리면 매번 config 파일을 복사해 값 하나만 바꾼 사본을 여러 개 만들게 된다.

```powershell
python app.py --config configs/baseline.json --result-dir outputs --experiment-name chunk-500 --chunk-size 500 --chunk-overlap 80
```

`--chunk-size`/`--chunk-overlap`/`--strategies`/`--k`/`--case-limit`처럼 자주 스윕하는 값만 CLI로 덮어쓸 수 있게 열어두고, 나머지(문서 경로, 평가 데이터 경로 등 실험 중 안 바뀌는 값)는 config에만 둔다. 실행에 실제로 쓰인 값은 덮어쓴 뒤의 최종 config를 그대로 `summary.json`에 함께 저장해야, 나중에 그 결과가 정확히 어떤 조건에서 나왔는지 알 수 있다.

config는 중첩된 dict를 그대로 쓰지 않고 `@dataclass`로 받았다(`DocumentConfig`/`ChunkingConfig`/`RetrievalConfig`/`MetricsConfig`/`GenerationConfig`). 이렇게 하면 각 dataclass의 기본값이 곧 "이 항목을 config에서 생략했을 때의 값"이 되고, JSON에 오타 난 키가 있으면 `ChunkingConfig(**raw["chunking"])`에서 `TypeError`로 바로 잡힌다. `raw.get("chunking", {})`처럼 섹션째로 생략도 허용하면, 실험마다 바꾸는 항목만 적은 짧은 config를 쓸 수 있다.

## golden set과 맞물리게 메타데이터를 먼저 정규화한다

Hit@k나 MRR은 결국 "검색된 문서의 메타데이터 == golden set의 정답 필드"라는 **정확한 일치 비교**다. 그래서 지표 코드보다 메타데이터 모양을 맞추는 게 먼저다. `PyPDFLoader`가 붙여주는 값과 golden set이 기대하는 값이 두 군데서 어긋난다.

- `source`가 **전체 경로**(`data/public/....pdf`)로 들어오는데, golden set의 `target_file_name`은 **파일명**만 갖고 있다.
- `page`가 **0부터** 시작하는데, golden set의 `target_page_no`는 사람이 보는 **1부터**의 페이지 번호다.

```python
for page in pages:
    page.metadata["source"] = Path(page.metadata["source"]).name
    page.metadata["page_no"] = page.metadata["page"] + 1
```

둘 중 하나만 어긋나도 모든 지표가 조용히 0으로 나온다. 예외도 경고도 없이 "검색 성능이 0"이라는 그럴듯한 결과가 나오기 때문에, 지표를 의심하기 전에 메타데이터를 먼저 확인해야 하는 종류의 버그다. 정규화는 **로드 시점에 한 번** 하고, 지표 함수(`file_hit_at_k`/`page_hit_at_k`/`reciprocal_rank`)는 정규화가 끝난 값을 단순 비교만 하게 두는 게 낫다 — 지표를 추가할 때마다 같은 변환을 반복해서 쓰면 그중 하나만 빠뜨리기 쉽다. `page`를 덮어쓰지 않고 `page_no`를 따로 만든 건 원본 값도 남겨두기 위해서다.

## 벡터스토어는 전략 수만큼 다시 만들지 않는다

Similarity·MMR·Hybrid는 모두 같은 벡터스토어를 쓴다. 전략마다 임베딩을 새로 만들면 문서 임베딩 API 호출이 전략 수만큼 늘어난다. 벡터스토어와 임베딩 객체를 한 번만 만들고 `as_retriever()`로 검색 방식만 다르게 구성하면, 문서 임베딩은 실행당 한 번으로 끝난다.

```python
if {"similarity", "mmr", "hybrid"} & set(strategies):   # 하나라도 필요할 때만 임베딩
    vectorstore = Chroma.from_documents(documents=documents, embedding=embeddings)
    similarity_retriever = vectorstore.as_retriever(search_kwargs={"k": k})
```

집합 교집합으로 "벡터 검색이 필요한 전략이 하나라도 있는지" 먼저 확인하는 것도 같은 이유다. `--strategies bm25`처럼 BM25만 돌릴 때는 임베딩 API를 아예 호출하지 않고 끝나서, 쿼터를 아끼며 반복 실험할 수 있다.

## 한국어 BM25는 토크나이저를 반드시 바꿔야 한다

BM25는 키워드 일치 기반이라 **토큰을 어떻게 쪼개는지가 성능을 그대로 결정한다.** `BM25Retriever`의 기본 전처리는 공백 분리에 가까워서, 한국어에서는 조사가 붙은 `정보화기본계획을`·`정보화기본계획은`·`정보화기본계획의`가 전부 다른 토큰이 된다. 질문과 문서가 같은 단어를 써도 조사만 다르면 일치가 안 잡힌다.

```python
_kiwi = Kiwi()   # 생성 비용이 크므로 모듈 수준에서 한 번만

def kiwi_tokenize(text: str) -> list[str]:
    tokens = _kiwi.tokenize(text)
    return [
        token.form.lower()
        for token in tokens
        if token.tag.startswith(("N", "V", "M", "X")) or token.tag in {"SL", "SN"}
    ]

bm25_retriever = BM25Retriever.from_documents(
    documents, preprocess_func=kiwi_tokenize, k=k
)
```

형태소 분석으로 조사·어미를 떼어내고, 품사 태그로 **내용어만 남긴다** — 체언(`N*`)·용언(`V*`)·수식언(`M*`)·어근접사(`X*`)에 외국어(`SL`)와 숫자(`SN`)를 더했다. 반대로 걸러지는 건 조사·어미·구두점처럼 어느 문서에나 나와서 변별력이 없는 토큰들이다. `SL`/`SN`을 일부러 살린 이유는 문서에 섞인 영문 약어나 연도·조항 번호가 오히려 정답을 특정하는 핵심 키워드인 경우가 많기 때문이다.

이 전처리는 옵션이 아니라 **결론을 좌우하는 전제**였다. 아래 스윕에서 BM25가 최고 성능을 낸 것도 이 토크나이저를 붙인 상태의 결과이고, 기본 토크나이저로 돌린 BM25 점수와는 비교 대상이 아니다. 이렇게 전략마다 딸린 전제가 결과를 바꾸는 경우, 스윕 표에 점수만 남기면 나중에 자기 결과를 자기가 오해하게 된다. (전략 자체의 개념은 [RAG 검색 고도화](RAG_검색고도화.md)에 정리해뒀다.)

## 진짜 문제: Gemini 무료 티어의 RPM 제한

문서 임베딩은 한 번만 하면 되지만, **질문(쿼리) 임베딩**은 놓치기 쉬운 중복이 있었다. Similarity 평가에서 질문을 임베딩하고, MMR 평가에서 같은 질문을 또 임베딩하고, Hybrid는 내부적으로 Similarity 검색기를 재사용하므로 한 번 더 임베딩한다 — 질문 35개짜리 평가를 전략 4개로 돌리면 같은 텍스트가 최대 3번씩 재임베딩된다.

이게 왜 문제가 되는지는 API에 짧은 시간 안에 여러 번 요청을 넣어보고 알았다. 20번 연속 임베딩 요청을 보내자 처음 5번은 바로 성공하고, 이후 14번은 전부 `429 RESOURCE_EXHAUSTED`가 났으며, 약 50초 뒤에야 다음 요청이 성공했다 — 분당 요청 수(RPM) 자체가 5회 안팎으로 매우 낮다는 뜻이다. 청크를 잘게 나눠 문서 임베딩 배치가 늘어나거나(700자 청크 402개 → 400자 청크 634개), 검색 전략을 여러 개 비교하느라 쿼리 임베딩이 중복되면 이 한도를 바로 넘긴다.

세 가지를 겹쳐서 대응했다.

```python
# 1) 재시도: 429가 나면 지수 백오프로 최대 8번 재시도
client = genai.Client(
    http_options=HttpOptions(
        retry_options=HttpRetryOptions(
            attempts=8, initial_delay=2.0, max_delay=60.0,
            exp_base=2, jitter=1.0,
        )
    ),
)
embeddings.client = client

# 2) 캐싱: 같은 질문 텍스트는 한 번만 임베딩
class RateLimitedEmbeddings(Embeddings):
    def embed_query(self, text):
        if text not in self._query_cache:
            self._wait_for_pace()
            self._query_cache[text] = self._embeddings.embed_query(text)
        return self._query_cache[text]

    # 문서 임베딩은 batch_size씩 끊고, 배치마다 페이싱을 통과시킨다
    def embed_documents(self, texts):
        results = []
        for i in range(0, len(texts), self._batch_size):
            self._wait_for_pace()
            results.extend(self._embeddings.embed_documents(texts[i : i + self._batch_size]))
        return results

    # 3) 페이싱: 요청 전에 최소 간격을 강제해 애초에 한도를 넘기지 않는다
    def _wait_for_pace(self):
        remaining = self._pace_seconds - (time.monotonic() - self._last_call_at)
        if remaining > 0:
            time.sleep(remaining)
        self._last_call_at = time.monotonic()
```

RPM은 "분당 **요청 수**"라서 요청 1건의 크기가 아니라 **횟수**가 한도에 걸린다. 그래서 문서 임베딩도 배치로 묶는 것만으로는 부족하고, 배치 하나하나가 페이싱을 통과해야 한다. 페이싱 대기는 `time.monotonic()`으로 재는데, 시스템 시각 변경에 영향받는 `time.time()`과 달리 단조 증가가 보장돼서 경과 시간 측정에는 이쪽이 맞다.

재시도만으로는 부족했다 — 청크 수가 많은 조건에서는 문서 임베딩 배치 자체가 8번 재시도로도 못 버티고 실패했다. 캐싱으로 쿼리 임베딩 호출을 최대 3배 줄이고, 페이싱으로 애초에 한도 근처에 안 가게 만든 뒤에야 안정적으로 끝까지 돌았다. 그래도 그날 실험을 많이 돌리면 **일일 쿼터** 자체가 소진돼 재시도·페이싱과 무관하게 최소 요청 1건도 429가 나는 경우가 있었다 — 이때는 시간이 지나 쿼터가 풀리길 기다리는 것 말고는 방법이 없었다.

## 캐싱을 넣은 순간 latency는 전략 비교 지표가 아니게 된다

위의 캐싱·페이싱에는 대가가 있었다. `summary.json`에 `latency_ms`를 남기고 있었는데, **이 값으로 전략 속도를 비교하면 안 된다.** 실제로 측정된 값을 보면 왜인지 바로 드러난다.

| experiment | Similarity | MMR | BM25 | Hybrid |
|---|---|---|---|---|
| baseline (700/100) | 1,507ms | 689ms | 5.8ms | 508ms |
| chunk-550 (550/75) | 12,364ms | 4.2ms | 2.0ms | 3.9ms |

`chunk-550`에서 MMR(4.2ms)과 Hybrid(3.9ms)가 BM25(2.0ms)와 비슷하게 나온 건 이들이 빠른 게 아니다. `retrieval.strategies` 순서상 **Similarity가 먼저 실행되면서 35개 질문의 임베딩을 전부 캐시에 채우고, 대기 시간까지 혼자 다 부담**했기 때문이다. 뒤에 오는 전략은 캐시 히트만 하니 API 왕복이 0이 된다. 같은 Similarity 전략이 실행마다 1,507ms와 12,364ms로 8배 넘게 벌어지는 것도 알고리즘 차이가 아니라 그 시점의 페이싱·쿼터 상태다.

정리하면 이렇다.

- **BM25의 숫자만 신뢰할 수 있다.** 임베딩 API를 아예 호출하지 않으므로 캐시·페이싱과 무관하게 항상 실제 검색 속도다.
- 나머지 전략의 값은 **실행 순서에 의존하는 부산물**이다. 첫 번째 전략에 페널티가 몰리고 이후 전략은 과소평가된다.
- 전략 간 속도를 정말 비교하려면 캐시를 끄고 전략을 하나씩 별도 실행해야 한다. 즉 이 실험 설계에서는 정확도와 속도를 동시에 측정할 수 없고, 어느 쪽을 볼지 정하고 설계를 맞춰야 한다.

지표를 계산해서 파일에 저장해두면 그 숫자가 자동으로 의미를 갖는 것처럼 보이는데, 최적화(캐싱)를 하나 넣는 순간 어떤 지표는 **측정 대상이 오염돼서 무효가 된다**. 저장은 계속하더라도 "이 값은 이런 이유로 비교에 쓰지 않는다"를 결과 문서에 같이 적어두지 않으면, 나중에 표만 보고 "MMR이 BM25만큼 빠르다"는 잘못된 결론을 낸다.

## 스윕 결과를 읽을 때 표본 크기를 함께 본다

문항 35개로 청크 크기와 검색 전략, `k`, Hybrid의 `hybrid_weights`를 스윕해봤다.

| experiment | chunk | 청크 수 | Similarity | MMR | BM25 | Hybrid |
|---|---|---|---|---|---|---|
| chunk-small | 400/50 | 634 | 0.874 | 0.852 | **0.924** | 0.900 |
| chunk-550 | 550/75 | 494 | 0.890 | 0.886 | 0.907 | **0.924** |
| baseline | 700/100 | 402 | 0.907 | 0.907 | 0.907 | 0.910 |

(MRR 기준. `chunk-1000`(1000/150, 청크 309개)도 돌리려 했지만 **API 일일 쿼터가 소진돼 완료하지 못했다** — 그래서 청크 크기 경향은 400~700자 구간에서만 확인한 것이다.)

- **청크 크기**가 가장 뚜렷한 차이를 만들었다. 400자+BM25와 550자+Hybrid가 MRR 0.924로 공동 1위였고(두 조합은 file_hit@1 0.971 / page_hit@1 0.914 / page_hit@3 0.943까지 전부 동일), 700자는 0.907~0.910이었다.
- **`k`**(5→10)는 결과가 완전히 동일했다 — 정답이 이미 상위 5위 안에서 발견되므로 더 늘려도 이득이 없었다. `k=3`은 오히려 낮았는데, `retrieval.k=3`이면 검색기가 애초에 3개만 반환해 `page_hit@5` 계산도 사실상 `page_hit@3`과 같아지는 구조적 한계가 섞여 있었다.
- **`hybrid_weights`**(0.3/0.7 ~ 0.7/0.3)는 MRR 차이가 0.005 이하였다.

문항 35개에서 MRR 차이 0.017은 질문 1개의 순위가 바뀌는 정도(1/35 ≈ 0.029)라 통계적으로 유의미하다고 보기 어렵다. 그래서 "550자+Hybrid가 최적"이라고 단정하지 않고, "이번 스윕 범위 안에서는 청크 크기가 k·hybrid_weights보다 결과에 큰 영향을 준다"처럼 표본 크기 대비 확실히 말할 수 있는 것만 결론으로 남겼다.

동률이 나온 두 조합 중에서는 **BM25 쪽이 실용적으로 유리했다.** 다만 이유를 측정된 latency 차이로 대면 안 된다(위 절 참고). BM25의 장점은 구조적인 것이다 — 임베딩 API를 아예 호출하지 않으니 429나 일일 쿼터 소진의 영향을 받지 않고, 페이싱 대기도 없다. 같은 정확도를 더 안정적으로 얻을 수 있다는 뜻이다.

**MMR에 대해서는 조건별로 결론이 갈렸다.** 청크가 작을 때(400·550자)는 MMR이 네 전략 중 확실히 가장 낮았고, `page_hit@5`도 400자에서 0.886으로 유일하게 0.9 아래였다 — 정답 문서가 상위권에 있는데 다양성 확보를 위해 밀어낸 것으로 보인다. 반면 700자에서는 Similarity·BM25와 **모든 지표가 소수점까지 완전히 동일**하게 나왔다(`fetch_k=20`에서 뽑은 상위 5개가 사실상 Similarity와 같았다는 뜻이다). "MMR이 항상 나쁘다"가 아니라 "청크가 작아 유사한 청크가 많이 생길 때 MMR의 다양성 페널티가 드러난다"가 이 데이터가 지지하는 범위다.

이 golden set은 정답이 키워드 매칭으로 풀리는 문항이 많아 BM25에 유리했을 가능성도 있다. 패러프레이즈나 동의어 위주의 질문이 많은 데이터셋이라면 Hybrid·Similarity가 더 유리해질 수 있어서, "BM25가 낫다"는 이 데이터셋 안에서의 결론으로만 남겨뒀다.

## 답변 생성까지 확장할 때 재사용한 것

검색 평가만 하던 스크립트에 [RAG 평가](RAG_평가.md)에서 쓴 것과 같은 `GroundedAnswer{answer, citations}` 구조화 출력과 규칙 기반 인용 검사(`valid_citation`/`relevant_citation`)를 그대로 가져왔다.

```python
retrieved_sources = {doc.metadata["source"] for doc in docs}
citations = set(result.citations)

# citations가 비어있지 않고 전부 검색된 파일 안에 있어야 근거 있는 인용이다
"valid_citation": bool(citations) and citations <= retrieved_sources,
"relevant_citation": case["target_file_name"] in citations,
```

`bool(citations)`가 빠지면 안 된다 — **공집합은 모든 집합의 부분집합**이라 `citations <= retrieved_sources`만 쓰면 LLM이 인용을 아예 안 했을 때 오히려 검사를 통과한다. 규칙 기반 검사를 부분집합·포함 관계로 쓸 때는 빈 값이 통과해버리는 경계를 매번 따로 막아야 한다.

원래 예시는 정답 출처가 여러 개일 수 있는 `relevant_sources` 리스트를 가정했는데, 이번 데이터셋은 문항당 정답 파일이 하나(`target_file_name`)뿐이라 `relevant_citation`을 집합 교집합 대신 단순 포함 여부로 단순화했다 — 같은 개념도 데이터 스키마에 맞춰 조건식을 다시 확인해야 한다. 생성은 API 호출 비용이 크므로 golden set 전체가 아니라 `case_limit`으로 소수 문항만 도는 것을 기본값으로 했다.

### 전부 1.0이 나온 지표는 좋은 결과가 아니다

그렇게 `case_limit=5`로 Similarity·Hybrid 두 전략을 돌린 결과는 `valid_citation_rate` 1.0, `relevant_citation_rate` 1.0 — **10건 전부 통과**였다.

만점이지만 이건 "생성 품질이 완벽하다"는 근거가 못 된다. 애초에 검색 단계의 `file_hit@1`이 0.971이라 5문항 안에서는 정답 파일이 거의 항상 1위로 잡히고, 그러면 LLM이 그 파일을 인용하는 것 말고 할 일이 거의 없다. **모든 조건에서 1.0이 나오는 지표는 전략을 구분할 변별력이 없다는 뜻**이고, 그 상태에서는 두 전략 중 어느 쪽이 나은지 이 지표로 말할 수 없다. 표본을 늘리거나(문항 수), 정답 출처가 여러 개인 문항이나 문서에 답이 없는 문항처럼 실패할 여지가 있는 케이스를 넣어야 지표가 정보를 갖기 시작한다. 지표를 설계할 때는 "잘하면 몇 점인지"만이 아니라 "**틀렸을 때 이 지표가 그걸 잡아낼 수 있는지**"를 같이 확인해야 한다.

## 참고

- [RAG 평가](RAG_평가.md) — 여기서 재사용한 Hit@k/MRR과 `GroundedAnswer` 인용 검사 원형
- [RAG 검색 고도화](RAG_검색고도화.md) — Similarity/MMR/BM25/Hybrid 전략 자체, 형태소 분석기를 붙인 BM25
- [LangChain 실행과 안정성](LangChain_실행과안정성.md) — `max_retries`/`with_fallbacks()`, 캐싱과 재시도의 일반적인 원리
