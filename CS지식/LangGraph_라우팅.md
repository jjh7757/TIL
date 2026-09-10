# LangGraph 라우팅 — Deterministic·LLM·Semantic·Hybrid

## Router가 하는 일

Router는 들어온 요청을 분류해서 적절한 처리 경로로 보낸다. 판단의 성격에 따라 방식을 조합한다.

```text
요청 → 빠르고 확실한 판단 → 전문 노드
              ↓ 애매함
           LLM 판단 → 전문 노드 또는 fallback
```

| 방식 | 적합한 판단 | 특징 |
|---|---|---|
| Deterministic | 형식·키워드처럼 확정 가능한 조건 | 빠르고 예측 가능함 |
| LLM | 맥락 해석이 필요한 의도 | 유연하지만 비용과 지연이 있음 |
| Semantic | 대표 문장과 의미가 가까운 요청 | 빠르지만 예시와 threshold에 민감함 |
| Hybrid | 확실한 요청과 애매한 요청이 섞인 환경 | 비용과 정확도의 균형을 잡기 쉬움 |

## Deterministic Routing

State 값을 명시적 규칙(키워드, 요청 유형, 주문 상태, 사용자 권한, 입력 형식 등)으로 검사해 경로를 정한다. 하나의 규칙만 일치하면 그 경로로, **충돌하거나 아무것도 일치하지 않으면 `uncertain`**을 반환하도록 설계한다 — "모르겠다"를 명시적인 값으로 표현해두면 이후 단계에서 그걸 보고 LLM에 넘기거나 재확인을 요청할 수 있다.

## LLM Routing

Structured Output으로 목적지 후보를 제한된 값(Literal 등)으로만 뽑는다. 여기서도 어느 경로에도 확실히 속하지 않는 경우를 위한 `uncertain`이 필요하다. `reason` 필드는 관찰·디버깅용으로만 쓰고, 실제 분기는 제한된 `category` 값으로만 한다 — **LLM이 만들어내는 confidence 같은 숫자는 보정된 확률이 아니므로 그대로 신뢰해서 분기 기준으로 쓰면 안 된다**는 게 중요한 지적이었다.

## Hybrid Routing과 Fallback

명확한 요청은 규칙(Deterministic)으로 빠르게 처리하고, 애매한 요청만 LLM으로 보낸다. LLM이 `uncertain`을 반환하거나 호출 자체가 실패하면 clarification(재확인) 경로로 보낸다. 규칙과 LLM을 섞을 때는 "규칙이 먼저 걸러내고 남은 것만 LLM에게"라는 순서가 핵심이다 — 이렇게 하면 확실한 요청에 굳이 LLM 비용을 쓰지 않는다.

## Semantic Routing

경로별 대표 문장을 미리 벡터 DB(Chroma 등)에 저장해두고, 들어온 요청과 가장 가까운 대표 문장의 metadata에서 경로를 가져온다. relevance score가 threshold보다 낮으면 LLM으로 fallback한다.

**주의**: 대표 문장과 threshold는 검증 데이터로 조정해야 하는 값이지, 감으로 정할 값이 아니다. threshold를 정할 때도 실험으로 성공률/실패율을 확인해서 적당한 값을 잡되, **그 숫자 자체를 정확한 것으로 과신하면 안 된다** — Semantic Routing은 "빠르지만 예시와 threshold에 민감하다"는 특징 그대로, 대표 문장 커버리지가 부족하면 엉뚱한 경로로 새기 쉽다.

## Flat Routing vs Hierarchical Routing

```text
Flat: User → Router → Refund
                    → Shipping
                    → Account
                    → Product

Hierarchical:
                    User
                     ↓
                Domain Router
              /       |       \
         Finance    Support   Engineering
            ↓          ↓          ↓
         Router      Router      Router
        /     \      /    \      /    \
      SQL    RAG   Refund FAQ  GitHub Logs
```

| 비교 | Flat | Hierarchical |
|---|---|---|
| Router 호출 | 보통 한 번 | 두 번 이상 가능 |
| 적합한 상황 | 목적지가 적음 | 목적지가 많고 계층이 명확함 |

목적지가 몇 개 안 되면 Flat이 단순하고 충분하다. 목적지가 많고 domain 경계가 뚜렷하면 Hierarchical이 관리·정확도 면에서 유리하지만, **여러 Router를 순차로 거치는 만큼 latency가 늘어난다**는 트레이드오프가 있다. 실습에서는 첫 Router가 세부 목적지를 직접 고르지 않고 domain(재무/지원/엔지니어링 등)만 고르고, 그 아래 하위 Router가 다시 세부 분류를 하는 2단계 구조로 구현했다.

## Router 평가 기준

- **routing accuracy**: 올바른 목적지를 선택한 비율
- **fallback rate**: 자동 분류하지 않고 보류(uncertain/clarification)한 비율
- **unsafe routing rate**: 위험한 잘못된 경로로 보낸 비율
- **latency**: 최종 처리까지 걸린 시간
- **token cost**: Router와 처리 노드가 합쳐서 쓴 전체 토큰

정확도 하나만 보지 않고 fallback rate·unsafe routing rate를 같이 보는 이유는, "애매하면 안전하게 보류시키는 것"과 "잘못 확신하고 틀린 곳으로 보내는 것"의 위험도가 다르기 때문이다. Router 설계에서는 후자를 줄이는 게 훨씬 중요하다.
