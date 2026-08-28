# 예산관리Agent — Gemini Function Calling 개인 예산 관리 Agent

AI Agent 엔지니어 부트캠프 파이썬 미니 프로젝트. 사용자가 자연어로 수입/지출을 기록하고
예산을 관리하면, Gemini의 Function Calling이 알맞은 도구를 골라 실행하는 CLI 에이전트를
구글 시트를 저장소로 삼아 구현했다.

## 무엇을 만들었나

- `sheets.py` — 구글시트(gspread) 읽기/쓰기 함수 전부. `get_worksheet`, `add_transaction`,
  `read_transactions`, `search_transactions`, `update_transaction`, `delete_transaction`,
  `set_budget`, `get_remaining_budget`, `save_monthly_report`, 입력 검증 함수
  (`validate_amount`/`validate_date`/`validate_month`/`validate_transaction_id`)
- `tools.py` — 위 함수들을 Gemini function-calling 스키마(`TOOL_LIST`)와 이름→함수
  매핑(`TOOL_FUNCTIONS`)으로 감싸는 계층
- `api.py` — `run_agent()`: Interactions API 호출 → `function_call` 스텝 실행 → 결과를
  다시 모델에 돌려주는 과정을 최대 턴 수 제한으로 도는 Agent loop. 모든 tool 호출을
  `tool_call_log.jsonl`에 기록
- `main.py` — 사용자 입력을 계속 받는 대화형 CLI 진입점
- `test_cases.py` — 함수 직접 호출 테스트와 자연어 Agent 테스트를 분리해 20여 개
  케이스로 구성. 실행 전후 거래 ID 스냅샷을 비교해 테스트가 새로 만든 거래만 자동으로 정리

## 실행 방법

```bash
pip install -r requirements.txt
```

1. Google Cloud Console에서 서비스 계정을 만들고 Sheets API·Drive API를 활성화한 뒤,
   JSON 키를 다운로드해 이 폴더에 `credentials.json`으로 저장
2. 사용할 구글 시트를 그 서비스 계정 이메일과 편집자 권한으로 공유
   (`거래내역`, `예산` 두 개의 시트 탭 필요 — 컬럼 구성은 `sheets.py`의 함수들 참고)
3. `.env.example`을 `.env`로 복사하고 `GEMINI_API_KEY`, `SPREADSHEET_ID` 채우기
4. 실행

```bash
python main.py          # 대화형 CLI로 실제 사용
python test_cases.py    # 함수 직접 호출 + 자연어 Agent 테스트 20여 개 실행
```

## 트러블슈팅 / 배운 점

### 1. tool 함수 시그니처와 호출 방식을 맞춰야 한다
`TOOL_FUNCTIONS`에 `lambda args: add_transaction(ws, **args)`처럼 딕셔너리를 언패킹해
넘기는 형태로 등록했는데, 처음엔 `execute_tool_call`에서 `tool_function(**step.arguments)`로
또 한 번 풀어서 넘겨서 `TypeError`가 났다. lambda가 "딕셔너리 하나"를 받게 만들었으면
호출부도 딕셔너리 하나로 넘겨야 한다 — 한쪽은 언패킹, 한쪽은 그대로 넘기는 식으로 섞이면
바로 깨진다.

### 2. ID/날짜 자동 채우기로 tool 스키마 단순화
초기엔 `add_transaction`이 `거래_ID`, `거래_날짜`까지 인자로 받았는데, Gemini가 이 값을
채워줄 이유가 없어서 스키마와 실제 필요 인자가 안 맞았다. `get_next_id()`(기존 ID 중
`max + 1` — `len + 1`을 쓰면 중간에 삭제된 행이 있을 때 중복 ID가 생김),
`date.today().isoformat()`로 함수 내부에서 자동 채우도록 바꾸고 나서야 스키마가 깔끔해졌다.

### 3. `additionalProperties: false`로도 LLM의 비결정성은 못 막는다
`set_budget(카테고리, 월, 예산금액)`을 호출할 때 Gemini가 가끔 `예산금액`과 함께 정의
안 된 `금액`(다른 tool에서 쓰는 파라미터 이름)을 같이 보내서 `TypeError` → 자동 재시도가
발생했다. JSON Schema에 `additionalProperties: false`를 추가해 완화는 됐지만 완전히
사라지진 않았다. 디버그 스크립트로 `interaction.steps`를 직접 까봐서 "재시도 자체가
정상적인 예외 처리 흐름"이라는 걸 확인했고, `set_budget`이 멱등적이라 실질적 피해는
없다는 결론으로 정리했다. 스키마 제약이 모델의 확률적 출력을 100% 보장하지는 못한다는
걸 실습으로 확인한 케이스.

### 4. 검색 결과가 여러 개면 Agent가 스스로 되묻게 만들기
`update_transaction`/`delete_transaction`을 거래 ID 없이 호출하려면 먼저
`search_transactions`로 찾아야 하는데, 검색 결과가 여러 건이면 Agent가 임의로 하나를
골라버릴 위험이 있다. `system_instruction`에 "결과가 2개 이상이면 조건을 더 물어보라"는
규칙을 넣었고, 실제로 같은 날짜·카테고리의 거래가 여러 건일 때 Agent가 사용자에게
특정 조건을 되묻는 것까지 확인했다.

### 5. 입력 검증 에러 메시지가 뭉개지지 않게 하기
`execute_tool_call`이 처음엔 모든 예외를 `except Exception`으로 잡아
`type(error).__name__`만 반환해서, `ValueError("금액은 0보다 커야 합니다: -5000")`처럼
구체적인 메시지를 만들어도 사용자에게는 "ValueError"라고만 전달됐다. `except ValueError`를
따로 잡아 `str(error)`를 반환하도록 고치니, Gemini가 그 메시지를 그대로 받아 "왜
실패했는지, 어떻게 고치면 되는지"까지 자연어로 설명해줬다.

### 6. 검증 함수 자체의 허점 — `strptime`은 생각보다 관대하다
`월` 형식을 `'YYYY-MM'`으로 강제하려고 `datetime.strptime(월, "%Y-%m")`만 썼는데,
`"2026-8"`(0패딩 없음)도 통과시켜버렸다. 거래 날짜는 항상 `date.today().isoformat()`로
0패딩되어 저장되니, `get_remaining_budget`의 `str(날짜).startswith(월)` 매칭이 영원히
실패하는 버그가 될 뻔했다. 정규식(`\d{4}-\d{2}`)으로 형식을 먼저 강제한 뒤 `strptime`으로
유효성까지 검사하는 이중 체크로 해결.

### 7. 빈 행(유령 데이터) 방어
구글시트에서 셀 값만 지우고 행 자체는 안 지우면(Delete 키 vs 행 삭제), `거래 ID`가 빈
문자열인 행이 남아 `int('')` 에러로 전체 기능이 죽었다. ID를 다루는 모든 함수
(`get_next_id`, `search_transactions`, `update_transaction`, `delete_transaction`,
`get_remaining_budget`)에 "ID가 빈 행은 건너뛴다"는 방어 코드를 넣어 해결. 근본 원인이
사용자의 시트 조작 방식이라 코드만으로 막는 데는 한계가 있다는 것도 확인.

### 8. 모듈 레벨 실행 vs 함수 호출 시점 실행
`.env` 로딩과 `SPREADSHEET_ID` 조회를 `get_worksheet()` 함수 안에 넣었다가, 파이썬은
모듈을 처음 import할 때 최상단 코드를 딱 한 번만 실행하고 이후엔 캐시한다는 걸 다시
확인하고 모듈 최상단으로 옮겼다. 설정값 로딩(한 번)과 매번 실행돼야 하는 동작(함수
호출마다)을 구분하는 게 핵심.

## 최종 결과

필수 시연 시나리오 5개(지출 등록, 조건 검색, 검색→수정 연속 호출, 예산 설정·조회, 존재하지
않는 거래 처리) 전부 통과. 선택 기능 중 거래 삭제, 월별 Markdown 보고서, tool 호출 로그
파일까지 구현. `test_cases.py` 20여 개 케이스(직접 호출 + 자연어 Agent 호출)로 검증하고,
실행 후 baseline과 비교해 테스트가 만든 거래만 자동으로 정리하도록 구성했다.
