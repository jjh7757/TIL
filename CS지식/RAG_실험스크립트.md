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

## 벡터스토어는 전략 수만큼 다시 만들지 않는다

Similarity·MMR·Hybrid는 모두 같은 벡터스토어를 쓴다. 전략마다 임베딩을 새로 만들면 문서 임베딩 API 호출이 전략 수만큼 늘어난다. 벡터스토어와 임베딩 객체를 한 번만 만들고 `as_retriever()`로 검색 방식만 다르게 구성하면, 문서 임베딩은 실행당 한 번으로 끝난다.

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

    # 3) 페이싱: 요청 전에 최소 간격을 강제해 애초에 한도를 넘기지 않는다
    def _wait_for_pace(self):
        remaining = self._pace_seconds - (time.monotonic() - self._last_call_at)
        if remaining > 0:
            time.sleep(remaining)
        self._last_call_at = time.monotonic()
```

재시도만으로는 부족했다 — 청크 수가 많은 조건에서는 문서 임베딩 배치 자체가 8번 재시도로도 못 버티고 실패했다. 캐싱으로 쿼리 임베딩 호출을 최대 3배 줄이고, 페이싱으로 애초에 한도 근처에 안 가게 만든 뒤에야 안정적으로 끝까지 돌았다. 그래도 그날 실험을 많이 돌리면 **일일 쿼터** 자체가 소진돼 재시도·페이싱과 무관하게 최소 요청 1건도 429가 나는 경우가 있었다 — 이때는 시간이 지나 쿼터가 풀리길 기다리는 것 말고는 방법이 없었다.

## 스윕 결과를 읽을 때 표본 크기를 함께 본다

문항 35개로 청크 크기(400/550/700/1000자)와 검색 전략, `k`, Hybrid의 `hybrid_weights`를 스윕해봤다.

- **청크 크기**는 뚜렷한 차이를 만들었다. 400자+BM25와 550자+Hybrid가 MRR 0.924로 공동 1위였고, 700자는 0.907~0.910이었다.
- **`k`**(5→10)는 결과가 완전히 동일했다 — 정답이 이미 상위 5위 안에서 발견되므로 더 늘려도 이득이 없었다. `k=3`은 오히려 낮았는데, `retrieval.k=3`이면 검색기가 애초에 3개만 반환해 `page_hit@5` 계산도 사실상 `page_hit@3`과 같아지는 구조적 한계가 섞여 있었다.
- **`hybrid_weights`**(0.3/0.7 ~ 0.7/0.3)는 MRR 차이가 0.005 이하였다.

문항 35개에서 MRR 차이 0.017은 질문 1개의 순위가 바뀌는 정도(1/35 ≈ 0.029)라 통계적으로 유의미하다고 보기 어렵다. 그래서 "550자+Hybrid가 최적"이라고 단정하지 않고, "이번 스윕 범위 안에서는 청크 크기가 k·hybrid_weights보다 결과에 큰 영향을 준다"와 "MMR은 모든 조건에서 꾸준히 가장 낮다"처럼 표본 크기 대비 확실히 말할 수 있는 것만 결론으로 남겼다. 동률이 나온 두 조합 중에서는 BM25 쪽이 임베딩 API를 쓰지 않아 속도(2~3ms vs 수백ms~수초)와 429 위험 모두에서 실용적으로 유리했다.

## 답변 생성까지 확장할 때 재사용한 것

검색 평가만 하던 스크립트에 [RAG 평가](RAG_평가.md)에서 쓴 것과 같은 `GroundedAnswer{answer, citations}` 구조화 출력과 규칙 기반 인용 검사(`valid_citation`/`relevant_citation`)를 그대로 가져왔다. 다만 원래 예시는 정답 출처가 여러 개일 수 있는 `relevant_sources` 리스트를 가정했는데, 이번 데이터셋은 문항당 정답 파일이 하나(`target_file_name`)뿐이라 `relevant_citation`을 집합 교집합 대신 단순 포함 여부(`target_file_name in citations`)로 단순화했다 — 같은 개념도 데이터 스키마에 맞춰 조건식을 다시 확인해야 한다는 걸 확인했다. 생성은 API 호출 비용이 크므로 golden set 전체가 아니라 `case_limit`으로 소수 문항만 도는 것을 기본값으로 하고, 필요하면 CLI로 전체 문항까지 늘릴 수 있게 열어뒀다.

## 참고

- [RAG 평가](RAG_평가.md) — 여기서 재사용한 Hit@k/MRR과 `GroundedAnswer` 인용 검사 원형
- [RAG 검색 고도화](RAG_검색고도화.md) — Similarity/MMR/BM25/Hybrid 전략 자체
- [LangChain 실행과 안정성](LangChain_실행과안정성.md) — `max_retries`/`with_fallbacks()`, 캐싱과 재시도의 일반적인 원리
