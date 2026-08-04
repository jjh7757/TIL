# 데이터 구조 초안

- 작성일: 2026-08-04
- 저장소: Supabase (PostgreSQL)
- 근거 교안: 4교시

---

## 0. 설계 원칙

교안 4교시는 개념 수준의 데이터 구조를 요구합니다. 이 프로젝트는 저장소가 Supabase로 확정되었으므로 **테이블 단위로 작성**합니다.

### 테이블을 5개로 줄인 이유

3교시에서 도메인 요소 12개를 찾았지만, 테이블은 5개입니다.

| 도메인 요소 | 저장 방식 |
|---|---|
| 사용자 | 단일 사용자이므로 테이블 없음. `chat_id`를 환경변수로 관리 |
| 모의투자 계좌 · 보유 종목 · 시세 · 접근토큰 | **저장하지 않음.** KIS에서 조회할 때마다 가져옵니다 |
| 종목 | `stocks` 테이블 |
| 주문 · 체결 | `orders` 테이블 (하나로 통합) |
| 판단 근거 | `rationales` 테이블 |
| 대화 세션 · 의도 | `conversation_context` 테이블 |
| 투자용어 | 테이블 없음. LLM이 생성하고 결과는 `event_logs`에 남김 |

**KIS에서 오는 데이터를 복제 저장하지 않습니다.** 잔고·시세는 실시간으로 변하므로 저장하면 곧 틀린 값이 됩니다. 조회 시점에 가져오고, 조회했다는 **사실만** 이벤트로 남깁니다.

### 주문 대기 상태를 별도 테이블로 만들지 않은 이유

`pending_orders`와 `orders`를 나누면 같은 주문이 두 테이블을 옮겨 다니며 상태 불일치가 생깁니다.

3교시에서 정의한 주문 상태 흐름이 이미 대기 단계를 포함하고 있습니다.

```
requested → awaiting_confirmation → awaiting_rationale → submitted → executed
```

따라서 **`orders` 테이블 하나에 `status` 컬럼으로 전 생애주기를 담습니다.** 대기 중인 주문은 `status`가 `awaiting_*`인 행입니다.

---

## 1. `stocks` — 종목 마스터

사용자가 종목명으로 말하면 종목코드를 찾기 위한 테이블입니다.

| 데이터 항목 | 타입 | 설명 | 필수 여부 |
|---|---|---|---|
| `stock_code` | `varchar(6)` PK | 종목코드 (`005930`) | 필수 |
| `stock_name` | `text` | 종목명 (`삼성전자`) | 필수 |
| `market` | `text` | 시장구분 (`KOSPI` / `KOSDAQ`) | 필수 |
| `is_active` | `boolean` | 조회·주문 대상 여부 | 필수 |
| `updated_at` | `timestamptz` | 갱신 시각 | 필수 |

**인덱스**: `stock_name`에 인덱스가 필요합니다. 모든 대화가 이 조회를 통과합니다.

> ⚠️ **범위 제한**: 전체 상장 종목을 적재하면 준비 시간이 늘어납니다. **코스피200 등 상위 200종목만 적재**하고, 목록에 없는 종목은 `지원하지 않는 종목입니다`로 안내합니다. (6교시 MoSCoW에서 확정)

### 종목명 모호성

`삼성전자`로 조회하면 `삼성전자`와 `삼성전자우`가 함께 나옵니다. 이때 **시스템이 임의로 고르지 않고 사용자에게 되묻습니다.** (예외 흐름 2.2)

---

## 2. 주문 테이블 — 기존 테이블을 확장합니다

> ⚠️ **이 테이블은 이미 존재하고 동작 중입니다.** 새로 만들지 않고 컬럼을 추가합니다.
> ⚠️ **확인 필요**: 실제 테이블명을 여기에 적어 두십시오.

### 2.1 현재 스키마 (동작 중)

| 컬럼 | 타입 | 설명 | 판정 |
|---|---|---|---|
| `id` | `int8` PK | 주문 식별자 (auto increment) | ✅ 그대로 사용. uuid 불필요 |
| `chat_id` | `text` | 요청한 텔레그램 사용자 | 🔴 **값 버그 있음** (2.2 참고) |
| `stock_code` | `text` | 대상 종목 | ✅ |
| `side` | `text` | `buy` / `sell` | ✅ |
| `qty` | `int4` | 주문 수량 | ✅ |
| `price` | `numeric` | 주문 단가. 시장가 주문이면 `NULL` | ✅ |
| `order_no` | `text` | KIS가 발급한 주문번호 | ✅ |
| `created_at` | `timestamptz` | 생성 시각 | ✅ |

### 2.2 🔴 `chat_id` 값 버그

실제 저장된 값:

```
chat_id: $('Telegram Trigger').item.json.messag...
```

**n8n 표현식이 평가되지 않고 문자열 그대로 저장되었습니다.** Supabase 노드 필드에 `=` 접두사를 붙이지 않아 리터럴로 들어간 경우입니다.

**이 버그가 망가뜨리는 것**

| 기능 | 이유 |
|---|---|
| 중복 주문 방지 | `chat_id` 부분 유니크 인덱스가 무용해집니다. 모든 행이 같은 문자열이므로 첫 주문 후 모든 주문이 차단됩니다. |
| 대화 맥락 조회 | `chat_id`로 맥락을 찾는데 실제 값이 없습니다. |
| 근거-사용자 연결 | 누가 어떤 근거로 주문했는지 추적할 수 없습니다. |
| 성공 기준 측정 | 사용자별 지표를 산출할 수 없습니다. |

**수정**: Supabase 노드의 `chat_id` 필드를 Expression 모드로 전환하거나 `=` 접두사를 붙입니다. 기존 2행은 테스트 데이터이므로 삭제합니다. **약 5분.**

### 2.3 추가할 컬럼

```sql
alter table <주문테이블>
  add column status text not null default 'requested',
  add column expected_price integer,
  add column expected_amount integer,
  add column reject_reason text,
  add column expires_at timestamptz,
  add column updated_at timestamptz default now();
```

| 추가 컬럼 | 왜 필요한가 |
|---|---|
| `status` | 주문 생애주기 관리. 없으면 `awaiting_confirmation` 같은 대기 상태를 담을 수 없습니다. |
| `expected_price` | **주문 시점에 사용자가 본 가격.** 시장가라 `price`는 `NULL`이므로, 이 값이 없으면 "저평가라고 판단했다"는 근거를 나중에 검증할 수 없습니다. |
| `expected_amount` | 예수금 검증과 사용자 안내에 사용 |
| `reject_reason` | 거부 사유 안내 |
| `expires_at` | 대기 상태 만료 처리 |
| `updated_at` | 상태 변경 추적 |

### `status` 값

| 값 | 의미 | 다음 처리 |
|---|---|---|
| `requested` | 의도 분류와 종목 해석 완료 | 예상 금액 계산, 예수금 확인 |
| `awaiting_confirmation` | 사용자 확인 대기 | 확인 응답 수신 |
| `awaiting_rationale` | 판단 근거 입력 대기 | 근거 선택·메모 수신 |
| `submitted` | KIS에 접수됨 | 체결 확인 |
| `executed` | 체결 완료 | 종료 |
| `rejected` | KIS가 거부 또는 사전 검증 실패 | 종료 (재시도 가능) |
| `expired` | 대기 중 만료 | 종료 |
| `cancelled` | 사용자가 취소 | 종료 |

### 🔴 중복 주문 방지 제약

```sql
-- 같은 chat_id에 진행 중인 주문은 1건만 허용
create unique index orders_one_active_per_chat
  on <주문테이블> (chat_id)
  where status in ('requested', 'awaiting_confirmation', 'awaiting_rationale');
```

**이 부분 유니크 인덱스가 예외 흐름 2.9(중복 주문)의 실질적 방어선입니다.** 애플리케이션 로직만으로 막으면 메시지가 빠르게 두 번 오는 경우를 놓칠 수 있습니다. n8n은 동시 실행이 가능하므로 실제로 발생합니다. DB 제약으로 막는 것이 확실합니다.

> ⚠️ **이 인덱스는 `chat_id` 버그를 고친 뒤에 만들어야 합니다.** 지금 만들면 모든 행의 `chat_id`가 같은 문자열이라 두 번째 주문부터 전부 차단됩니다.

### 🔴 만료 처리

`expires_at`이 지난 `awaiting_*` 행은 `expired`로 바꿔야 합니다. 없으면 며칠 뒤 사용자가 보낸 `네`가 옛 주문을 실행합니다.

처리 방법: 주문 흐름을 시작할 때마다 만료된 행을 먼저 정리합니다. (별도 스케줄러 없이 처리)

**만료 시간 기준**: `awaiting_confirmation` 10분, `awaiting_rationale` 10분

### 🔴 구조 변경: `create: row` → `update: row`

현재 주문 서브워크플로우의 마지막 노드는 `데이터베이스에 주문 기록` (`create: row`)입니다. **주문이 성공한 뒤에 행을 만듭니다.**

그래서 두 가지 문제가 있습니다.

1. **거부된 주문은 기록이 남지 않습니다.** 근거 기록률 계산식의 분모(`order_submitted + order_rejected`)가 채워지지 않습니다.
2. **대기 상태를 담을 행이 없습니다.** `awaiting_confirmation`, `awaiting_rationale`은 KIS 호출 **전**의 상태입니다.

**변경 후 흐름**

```
메인: 주문 행 생성 (status = requested)
→ 확인 단계 (status = awaiting_confirmation)
→ 근거 입력 (status = awaiting_rationale)
→ 주문 서브워크플로우 호출 (order_id 전달)
→ 서브: 주문 실행
→ 서브: 행 UPDATE (order_no, status = submitted 또는 rejected)
```

**작업**: 주문 서브워크플로우가 `order_id`를 파라미터로 받도록 하고, 마지막 노드를 `update: row`로 바꿉니다. **약 1h.**

---

## 3. `rationales` — 판단 근거 (신규)

**이 프로젝트의 성공 기준을 측정하는 유일한 테이블입니다.**

| 데이터 항목 | 타입 | 설명 | 필수 여부 |
|---|---|---|---|
| `id` | `int8` PK | 근거 식별자 | 필수 |
| `order_id` | `int8` FK | 연결된 주문 (주문 테이블의 `id`) | 필수 |
| `reason_type` | `text` | 선택한 근거 유형 | 필수 |
| `reason_memo` | `text` | 추가로 적은 내용 | 선택 |
| `created_at` | `timestamptz` | 입력 시각 | 필수 |

### `reason_type` 선택지

텔레그램 인라인 키보드로 제시합니다.

| 값 | 표시 문구 |
|---|---|
| `undervalued` | 저평가라고 판단 |
| `earnings` | 실적이 좋아짐 |
| `industry` | 업황이 좋아 보임 |
| `news` | 뉴스나 이슈를 봄 |
| `dividend` | 배당을 기대 |
| `gut` | 그냥 감 |

> `그냥 감`을 선택지에 넣은 이유: 없으면 사용자가 아무거나 고릅니다. **그러면 데이터가 오염되고 측정값을 믿을 수 없게 됩니다.** 정직한 선택지를 주면 `gut` 비율 자체가 의미 있는 지표가 됩니다. 프로젝트 목적은 `gut` 비율을 줄이는 것입니다.

### 실패한 주문의 근거도 남깁니다

주문이 거부되어도 `rationales` 행을 삭제하지 않습니다. **사용자가 근거를 만들었다는 사실은 유효**하며, 성공 기준 측정에 포함시킵니다. (예외 흐름 2.7)

---

## 4. `conversation_context` — 대화 맥락

`그거 10주 사줘`의 "그거"를 해석하기 위한 테이블입니다. **n8n에서 가장 까다로운 지점을 이 테이블이 해결합니다.**

| 데이터 항목 | 타입 | 설명 | 필수 여부 |
|---|---|---|---|
| `chat_id` | `text` PK | 텔레그램 사용자 | 필수 |
| `last_stock_code` | `varchar(6)` | 마지막으로 다룬 종목 | 선택 |
| `last_intent` | `text` | 마지막으로 분류된 의도 | 선택 |
| `last_message` | `text` | 마지막 사용자 메시지 원문 | 선택 |
| `updated_at` | `timestamptz` | 갱신 시각 | 필수 |

**`chat_id`를 PK로 두고 매 턴 upsert합니다.** 대화 이력을 전부 쌓지 않습니다. 이유:

- 5일 일정에서 필요한 것은 **직전 맥락 1개**입니다. `그거`는 항상 가장 최근 종목을 가리킵니다.
- 전체 이력은 `event_logs`에 남으므로 분석에 필요하면 거기서 재구성할 수 있습니다.

> ⚠️ 맥락에도 유효기간이 필요합니다. `updated_at`이 30분 이상 지났으면 `그거`를 해석하지 않고 `어느 종목을 말씀하시는지 다시 알려주세요`로 되묻습니다. 어제 본 종목을 오늘 `그거`로 주문하면 사고입니다.

---

## 5. `event_logs` — 이벤트 기록

| 데이터 항목 | 타입 | 설명 | 필수 여부 |
|---|---|---|---|
| `id` | `int8` PK | 이벤트 식별자 | 필수 |
| `event_name` | `text` | 이벤트 이름 (과거형 `snake_case`) | 필수 |
| `event_category` | `text` | `domain` / `operation` | 필수 |
| `chat_id` | `text` | 관련 사용자 | 선택 |
| `order_id` | `int8` | 관련 주문 | 선택 |
| `payload` | `jsonb` | 이벤트별 상세 내용 | 선택 |
| `occurred_at` | `timestamptz` | 발생 시각 | 필수 |

`payload`를 `jsonb`로 둔 이유: 이벤트마다 담을 내용이 달라서 컬럼을 미리 고정할 수 없습니다. 예를 들어 `intent_classification_failed`는 원문을, `stock_ambiguous`는 후보 목록을 담습니다.

자세한 이벤트 정의는 [[03_event_catalog|이벤트 카탈로그]]를 참고합니다.

---

## 6. 저장하지 않는 데이터

| 데이터 | 저장하지 않는 이유 |
|---|---|
| 예수금·보유종목·수익률 | 실시간으로 변합니다. 저장하면 곧 틀린 값이 됩니다. 조회 시점에 KIS에서 가져옵니다. |
| 현재가·등락률·거래량 | 동일 |
| KIS 접근토큰 | n8n Credential이 관리합니다. DB에 두면 유출 위험이 커집니다. |
| 계좌번호 | n8n Credential 또는 환경변수. **DB·문서·발표자료에 남기지 않습니다.** |
| LLM이 생성한 설명문 전문 | 매번 새로 생성합니다. 저장 가치가 낮고 용량만 늘어납니다. 생성했다는 사실만 이벤트로 남깁니다. |

---

## 7. 개인정보 취급

교안 8교시의 API Key 관리 원칙과 7교시 완료의 정의(`개인정보가 화면, 문서 또는 로그에 그대로 기록되지 않습니다`)를 적용합니다.

| 데이터 | 취급 |
|---|---|
| `chat_id` | 개인 식별이 가능합니다. DB에는 저장하되 **발표자료·시연 영상·README에는 가립니다.** |
| 계좌번호 | 저장하지 않습니다. 노출 금지. |
| KIS 앱키·시크릿 | n8n Credential. 워크플로우 JSON 내보내기 시 포함 여부 확인. |

> 🔴 **발표 준비 시 반드시 확인**: 시연 영상과 발표자료 스크린샷에 계좌번호, `chat_id`, 실행 로그의 토큰값이 보이지 않는지 확인합니다.

---

## 8. 전체 관계

```
stocks ──┐
         ├─< orders ──< rationales
         │
conversation_context ──> (last_stock_code로 stocks 참조)

event_logs ──> orders (order_id, 선택적)
```

---

## 관련 문서

- [[02_data_sources|데이터 소스]]
- [[03_event_catalog|이벤트 카탈로그]]
- [[04_naming_convention|용어와 네이밍 컨벤션]]
- [[../02_Domain/03_workflow|정상·예외 업무 흐름]]
