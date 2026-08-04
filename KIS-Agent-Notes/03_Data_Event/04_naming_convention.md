# 용어와 네이밍 컨벤션

- 작성일: 2026-08-04
- 근거 교안: 4교시

---

## 1. 네이밍 컨벤션이란?

프로젝트에서 **같은 대상을 같은 이름으로 표현하기 위한 공통 규칙**입니다.

혼자 하는 프로젝트인데도 규칙이 필요한 이유:

| 이유 | 설명 |
|---|---|
| 5일 뒤의 나는 남입니다 | Day 1에 `stock_cd`로 쓰고 Day 4에 `stock_code`로 쓰면 디버깅 시간이 늘어납니다. |
| n8n 노드 이름이 흐름을 설명해야 합니다 | 노드가 수십 개가 되면 이름만으로 흐름을 읽을 수 있어야 합니다. |
| Supabase 컬럼과 n8n 변수가 일치해야 합니다 | 이름이 다르면 매핑 코드를 따로 써야 하고, 그 자리가 버그 온상이 됩니다. |
| 발표에서 설명해야 합니다 | 용어가 흔들리면 발표가 흔들립니다. |

---

## 2. 공식 용어

한 대상에 하나의 이름만 씁니다. **아래 표의 오른쪽 이름만 사용합니다.**

| 한글 공식 용어 | 영문 기준 이름 | 고유 번호 | 쓰지 않을 표현 |
|---|---|---|---|
| 사용자 | `user` | `chat_id` | 유저, 회원, 고객, `telegram_id` |
| 종목 | `stock` | `stock_code` | 주식, 티커, `symbol`, `ticker`, `code` |
| 종목명 | `stock_name` | — | 주식이름, `name`, `stock_nm` |
| 시세 | `quote` | — | 가격, `price_info`, `market_data` |
| 현재가 | `current_price` | — | 가격, `price`, `now_price` |
| 계좌 | `account` | — | 어카운트, 계정 |
| 예수금 | `deposit` | — | 잔액, 현금, `cash`, `balance` |
| 보유 종목 | `holding` | — | 포지션, 잔고, `position` |
| 주문 | `order` | `id` (주문 테이블 PK) | 거래, 매매, `trade` |
| KIS 주문번호 | `order_no` | — | `order_number`, `odno`, `kis_order_no` |
| 매수·매도 구분 | `side` | — | 매매구분, `type`, `buy_sell`, `order_side` |
| 주문 수량 | `qty` | — | 수량, `quantity`, `amount` |
| 체결 | `execution` | — | 약정, `fill`, `filled` |
| **판단 근거** | `rationale` | `rationale_id` | 이유, 사유, `reason`, `why` |
| 근거 유형 | `reason_type` | — | 근거종류, `rationale_type` |
| 의도 | `intent` | — | 명령, 요청종류, `command` |
| 대화 맥락 | `conversation_context` | — | 세션, 히스토리, `session`, `history` |
| 접근토큰 | `access_token` | — | 토큰, `token`, `auth` |
| 투자용어 | `term` | — | 용어, 단어, `keyword` |

### 헷갈리기 쉬운 구분

| 구분해야 할 대상 | 이름 | 차이 |
|---|---|---|
| 내부 주문 식별자 / KIS 주문번호 | `id` / `order_no` | 앞은 우리 테이블의 PK, 뒤는 KIS가 준 번호. **섞으면 조회가 실패합니다.** |
| 주문 시점 예상가 / 실제 주문 단가 | `expected_price` / `price` | 시장가 주문이면 `price`는 `NULL`입니다. **근거 검증에는 `expected_price`가 필요합니다.** |
| 예상 금액 / 실제 체결 금액 | `expected_amount` / (이번 범위 밖) | 앞은 요청 시점의 추정치입니다. |
| 근거 유형 / 근거 메모 | `reason_type` / `reason_memo` | 앞은 선택지 코드, 뒤는 자유 텍스트 |
| 예수금 / 보유 종목 평가금액 | `deposit` / `holding` | 둘 다 "잔고"로 불리기 쉽습니다. 구분합니다. |

---

## 3. 이름 규칙

### 3.1 공통

- 고유 번호는 이름 뒤에 `_id`를 붙입니다. (`order_id`, `rationale_id`)
- 여러 영문 단어는 소문자와 밑줄을 쓰는 `snake_case`로 작성합니다.
- 같은 대상은 문서·DB·n8n·이벤트에서 **같은 뿌리 단어**를 씁니다.
- 시각 컬럼은 `_at`으로 끝냅니다. (`created_at`, `expires_at`)
- 참·거짓 값은 `is_`로 시작합니다. (`is_active`)
- 새로 만드는 이름에는 합의하지 않은 줄임말을 쓰지 않습니다.

### ⚠️ 예외: 이미 동작 중인 컬럼 이름은 바꾸지 않습니다

주문 테이블은 이미 존재하고 동작 중입니다. 다음 이름은 **줄임말이지만 그대로 유지합니다.**

| 실제 컬럼 | 원래 규칙대로라면 | 유지하는 이유 |
|---|---|---|
| `qty` | `quantity` | 동작 중인 Supabase 노드의 필드 매핑을 건드려야 함 |
| `side` | `order_side` | 동일 |
| `order_no` | `kis_order_no` | 동일 |
| `id` | `order_id` | PK로 이미 사용 중 |

**5일 일정에서 동작하는 코드의 컬럼명을 바꾸는 것은 순수한 리스크입니다.** 얻는 것은 이름의 일관성뿐이고, 잃을 수 있는 것은 주문 기능 전체입니다.

이 문서 7장의 원칙을 스스로에게 적용한 결과입니다 — *규칙을 지키다 막히면 규칙을 어기지 말고 문서를 고칩니다.*

단, **새로 만드는 테이블(`rationales`, `event_logs`, `conversation_context`, `stocks`)에는 줄임말을 쓰지 않습니다.**

### 3.2 `snake_case`란?

여러 영문 단어를 **소문자와 밑줄**로 연결하는 방식입니다.

```
stock_code       ✅
stockCode        ❌ camelCase
StockCode        ❌ PascalCase
stock-code       ❌ kebab-case
```

Supabase(PostgreSQL)가 기본적으로 소문자를 쓰기 때문에 `snake_case`가 자연스럽습니다. `stockCode`로 만들면 조회할 때마다 큰따옴표를 붙여야 합니다.

### 3.3 이벤트 이름 — 과거형

이벤트는 **이미 발생한 사건**입니다. 따라서 과거형으로 씁니다.

```
order_submitted     ✅ 접수되었다
order_submit        ❌ 접수하라 (명령)
submit_order        ❌ 주문 접수 (동작)
```

**왜 이 구분이 중요합니까?**

| 이름 | 읽히는 의미 |
|---|---|
| `submit_order` | *앞으로* 주문을 접수하는 동작 → 함수 이름 |
| `order_submitted` | 주문이 *이미* 접수된 사실 → 이벤트 이름 |

이벤트는 되돌릴 수 없는 사실의 기록입니다. 과거형이 그 성질을 이름에 담습니다.

### 3.4 이벤트 이름 구조

```
<대상>_<과거형 동작>
```

```
order_requested
order_confirmed
rationale_recorded
stock_resolved
token_refreshed
```

실패 이벤트는 `_failed`, 차단 이벤트는 `_blocked`로 끝냅니다.

```
intent_classification_failed
token_refresh_failed
duplicate_order_blocked
unauthorized_access_blocked
```

---

## 4. n8n 워크플로우·노드 이름 규칙

n8n은 이름 규칙이 없으면 금방 읽을 수 없게 됩니다.

### 4.1 워크플로우

| 종류 | 규칙 | 예시 |
|---|---|---|
| 메인 | `main_<역할>` | `main_telegram_agent` |
| 서브 | `sub_<대상>_<동작>` | `sub_kis_token_refresh`, `sub_kis_balance_get`, `sub_kis_quote_get`, `sub_kis_order_place` |

> 기존 워크플로우 이름이 다르면 **바꾸지 않아도 됩니다.** 5일 일정에서 이름 변경은 위험한 작업입니다. 대신 이 문서에 실제 이름을 기록해 두십시오.
>
> ⚠️ **확인 필요**: 실제 워크플로우 이름 5개를 이 표에 적어 두면 문서와 구현이 일치합니다.

### 4.2 노드 이름

```
<동작> - <대상>
```

```
분류 - 사용자 의도
조회 - 종목코드
조회 - KIS 시세
검증 - 예수금
저장 - 판단 근거
호출 - 주문 서브워크플로우
전송 - 텔레그램 메시지
기록 - 이벤트 로그
```

**기본 노드 이름(`HTTP Request1`, `Set2`)을 그대로 두지 않습니다.** 노드가 30개를 넘으면 어떤 게 무엇인지 알 수 없게 되고, 디버깅에서 시간을 잃습니다.

---

## 5. 의도(Intent) 이름

의도 분류 결과로 쓸 값입니다. 이 목록이 곧 분기 조건이 됩니다.

| 의도 | 값 | 사용자 발화 예시 |
|---|---|---|
| 용어 질문 | `ask_term` | `PER이 뭐야?` |
| 계좌 진단 | `check_account` | `내 계좌 어때?` |
| 시세 조회 | `check_quote` | `삼성전자 어때?` |
| 매수 주문 | `place_buy_order` | `10주 사줘` |
| 매도 주문 | `place_sell_order` | `절반 팔아줘` |
| 확인 응답 | `confirm` | `네`, `응`, `진행해` |
| 취소 응답 | `cancel` | `아니요`, `취소` |
| 전략 질문 | `ask_strategy` | `분산투자가 뭐야?` |
| 판별 불가 | `unknown` | `음...` |

> `confirm`과 `cancel`을 의도로 둔 이유: 주문 확인 단계에서 사용자가 `네` 말고 `그래 해줘`, `ㅇㅇ`, `좋아` 라고 답할 수 있습니다. **문자열 비교로는 못 잡습니다.** 의도 분류를 통과시켜야 합니다.

---

## 6. 상태 값 이름

| 대상 | 값 |
|---|---|
| 주문 상태 | `requested`, `awaiting_confirmation`, `awaiting_rationale`, `submitted`, `executed`, `rejected`, `expired`, `cancelled` |
| 매수·매도 | `buy`, `sell` |
| 근거 유형 | `undervalued`, `earnings`, `industry`, `news`, `dividend`, `gut` |
| 이벤트 분류 | `domain`, `operation` |
| 시장구분 | `KOSPI`, `KOSDAQ` |

상태 값은 **현재 단계**를 나타내므로 과거형을 쓰지 않습니다. 이벤트만 과거형입니다.

```
상태: awaiting_confirmation   (지금 확인을 기다리는 중)
이벤트: order_confirmed        (확인이 완료된 사실)
```

---

## 7. 이 문서를 어길 때

5일 일정에서 규칙을 지키다 막히면, **규칙을 어기지 말고 이 문서를 고치십시오.** 그리고 고친 내용을 기준선 변경 기록에 남깁니다.

문서와 구현이 다른 상태가 가장 위험합니다. 문서를 믿고 코드를 짜다가 틀리기 때문입니다.

---

## 관련 문서

- [데이터 구조 초안](01_data_structure.md)
- [데이터 소스](02_data_sources.md)
- [이벤트 카탈로그](03_event_catalog.md)
