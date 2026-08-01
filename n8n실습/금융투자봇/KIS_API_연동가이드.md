# 한국투자증권 Open API 연동 가이드 (n8n HTTP Request 노드 설정값)

> ⚠️ 아래 tr_id·파라미터명은 기억을 바탕으로 정리한 것으로, 실제 호출 전에
> [KIS Developers 포털 문서](https://apiportal.koreainvestment.com)와
> [공식 예제 repo (koreainvestment/open-trading-api)](https://github.com/koreainvestment/open-trading-api)에서
> 최신 스펙과 대조해서 확인할 것. 특히 주문 API는 필드 하나만 틀려도 에러가 나거나
> 의도와 다른 주문이 나갈 수 있으니 모의투자 환경에서 충분히 테스트 후 실제 사용.

## Base URL

- 모의투자: `https://openapivts.koreainvestment.com:29443`
- (참고, 이 프로젝트에서는 사용 안 함) 실전투자: `https://openapi.koreainvestment.com:9443`

이 프로젝트는 전부 모의투자 base URL을 사용한다.

---

## 1. 토큰 발급/갱신 (별도 스케줄 워크플로우)

접근 토큰은 유효기간이 길고(약 24시간) 발급 자체에 횟수 제한이 있으므로,
매번 새로 발급하지 않고 Supabase `kis_token` 테이블에 캐시해서 재사용한다.

**서브워크플로우 "Get Valid KIS Token" 로직**

1. Supabase(Select) `kis_token` where `id = 1`
2. IF `expires_at`이 5분 이상 남아있으면 → 그 `access_token`을 그대로 반환하고 종료
3. ELSE → HTTP Request로 신규 발급:
   - Method: `POST`
   - URL: `{base}/oauth2/tokenP`
   - Headers: `content-type: application/json`
   - Body (JSON):
     ```json
     {
       "grant_type": "client_credentials",
       "appkey": "{{appkey}}",
       "appsecret": "{{appsecret}}"
     }
     ```
   - 응답의 `access_token`, `expires_in`(초)을 받아서
     `expires_at = now() + expires_in초`로 계산
4. Supabase(Update) `kis_token` id=1에 새 토큰/만료시각 저장
5. `access_token` 반환

이 서브워크플로우를 다른 모든 tool 서브워크플로우 맨 앞에서 호출해서 토큰을 받아 쓴다.

---

## 2. 시세조회 Tool

- Method: `GET`
- URL: `{base}/uapi/domestic-stock/v1/quotations/inquire-price`
- Headers:
  - `authorization: Bearer {access_token}`
  - `appkey: {appkey}`
  - `appsecret: {appsecret}`
  - `tr_id: FHKST01010100`
  - `custtype: P`
- Query Params:
  - `FID_COND_MRKT_DIV_CODE: J`
  - `FID_INPUT_ISCD: {종목코드 6자리}`
- 응답에서 뽑아 쓸 값: `output.stck_prpr`(현재가), `output.prdy_vrss`(전일대비), `output.prdy_ctrt`(전일대비율)

Agent에게는 종목코드가 아니라 종목명("삼성전자")으로 들어오므로, 자주 쓰는 종목
이름→코드 매핑을 Set 노드나 별도 조회 테이블로 준비해두는 게 편하다 (예: 삼성전자=005930).

---

## 3. 모의계좌 잔고조회 Tool

- Method: `GET`
- URL: `{base}/uapi/domestic-stock/v1/trading/inquire-balance`
- Headers:
  - `authorization: Bearer {access_token}`
  - `appkey`, `appsecret`
  - `tr_id: VTTC8434R` (모의투자 잔고조회)
  - `custtype: P`
- Query Params (계좌번호는 모의투자 신청 시 발급받은 계좌번호를 앞 8자리/뒤 2자리로 분리):
  - `CANO: {계좌번호 앞 8자리}`
  - `ACNT_PRDT_CD: {계좌번호 뒤 2자리}`
  - `AFHR_FLPR_YN: N`
  - `OFL_YN:` (빈값)
  - `INQR_DVSN: 02`
  - `UNPR_DVSN: 01`
  - `FUND_STTL_ICLD_YN: N`
  - `FNCG_AMT_AUTO_RDPT_YN: N`
  - `PRCS_DVSN: 01`
  - `CTX_AREA_FK100:` (빈값)
  - `CTX_AREA_NK100:` (빈값)
- 응답: `output1`(보유종목별 배열), `output2`(계좌 총평가금액 등 요약)

---

## 4. 모의 매수/매도 주문 Tool

주문은 body 위변조 방지를 위해 hashkey를 먼저 발급받아 헤더에 넣어야 한다.

**4-1. hashkey 발급**

- Method: `POST`
- URL: `{base}/uapi/hashkey`
- Headers: `content-type: application/json`, `appkey`, `appsecret`
- Body: 아래 4-2에서 보낼 주문 body와 **동일한 JSON**
- 응답의 `HASH` 값을 다음 요청 헤더에 사용

**4-2. 주문 실행**

- Method: `POST`
- URL: `{base}/uapi/domestic-stock/v1/trading/order-cash`
- Headers:
  - `authorization: Bearer {access_token}`
  - `appkey`, `appsecret`
  - `tr_id: VTTC0802U` (매수) / `VTTC0801U` (매도)
  - `custtype: P`
  - `hashkey: {4-1에서 받은 HASH}`
- Body (JSON):
  ```json
  {
    "CANO": "{계좌번호 앞 8자리}",
    "ACNT_PRDT_CD": "{계좌번호 뒤 2자리}",
    "PDNO": "{종목코드}",
    "ORD_DVSN": "01",
    "ORD_QTY": "{수량}",
    "ORD_UNPR": "0"
  }
  ```
  - `ORD_DVSN: 01`은 시장가, `ORD_UNPR: 0`은 시장가 주문 시 관례
- 응답: `output.ODNO`(주문번호) → `trade_log` 테이블에 기록

**중요**: Agent 프롬프트에 "주문 tool을 호출하기 전 반드시 사용자에게 종목/수량/매수매도 여부를
재확인 질문을 하고, 명확한 긍정 답변을 받은 다음에만 tool을 호출하라"는 지침을 넣을 것.
n8n AI Agent 노드의 System Message에 이 규칙을 명시한다.

---

## n8n에서 조립하는 방법

1. 위 1~4를 각각 **별도의 서브워크플로우**로 만든다 (Webhook 대신 "Execute Workflow Trigger"로 시작).
2. 메인 봇 워크플로우의 AI Agent 노드에 각 서브워크플로우를 **"Call n8n Workflow Tool"** 노드로 연결한다.
   - Tool 설명(description)에 "언제 이 tool을 써야 하는지"를 자연어로 명확히 적어야
     Gemini가 상황에 맞게 올바른 tool을 고른다. 예: "특정 종목의 현재가와 등락률을 조회할 때 사용. input: 종목코드(6자리)"
3. Agent 노드의 System Message에 아래 내용을 포함:
   - 모의투자 환경이라는 것을 사용자에게 알릴 것
   - 주문 전 반드시 재확인
   - 모르는 종목코드는 추측하지 말고 사용자에게 다시 물어볼 것
4. Supabase 노드는 `service_role` 키로 연결 (RLS를 무시하고 `alerts`/`trade_log`/`kis_token` 테이블에 접근).

## 다음 단계 제안

1. n8n Cloud에서 "Get Valid KIS Token" 서브워크플로우부터 만들고 단독 실행으로 토큰이 잘 나오는지 확인
2. 시세조회 tool 서브워크플로우 → 단독 실행 테스트
3. 메인 워크플로우(Telegram Trigger + AI Agent)에 시세조회 tool만 연결해서 "삼성전자 지금 얼마야?" 테스트
4. 잔고조회, 알림 등록 tool 순서로 추가
5. 마지막에 주문 tool 추가 (재확인 로직 꼭 테스트)
