# LangGraph Agent Tool 실행 검증과 통제

Agent는 사용자 요청에 따라 실행할 Tool과 인자를 **제안**할 뿐이다. Tool을 실제로 실행하는 프로그램은 인자·사용자 권한·승인 여부를 확인하고 허용된 작업만 실행해야 한다 — LLM이 무엇을 하자고 제안하든, 실행 여부는 코드가 결정한다는 원칙이다.

## Middleware 구조

Middleware는 모델이나 Tool 호출 전후에 공통 처리를 끼워 넣는 기능이다. `create_agent(middleware=[...])`로 등록한다.

```text
agent 시작 → before_agent → before_model → [model call ← wrap_model_call] → after_model
   ├─ tool call 있음 → [tool execution ← wrap_tool_call] → 다시 before_model로
   └─ tool call 없음 → after_agent
```

`wrap_model_call`/`wrap_tool_call`은 해당 호출을 감싸 실행 전후를 처리하거나 아예 차단할 수 있다. Tool 호출이 여러 개면 `wrap_tool_call`은 각 호출마다 적용된다.

`@wrap_tool_call`로 만든 함수는 `request`(현재 Tool 호출 정보, `request.tool_call`로 이름·인자 확인)와 `handler`(다음 처리로 넘기는 함수)를 받는다. `handler(request)`를 호출하면 다음 Middleware나 실제 Tool 실행으로 이어지고, **호출하지 않고 `ToolMessage`를 반환하면 Tool 실행 자체를 차단**한다. 단, 실행 후 검사는 이미 벌어진 부수효과(DB 저장 등)를 되돌리지 못한다는 한계는 그대로다.

## State vs Context

| 구분 | 전달하는 주체 | 예 |
|---|---|---|
| Tool 인자 | LLM이 호출을 제안할 때 생성 | 조회할 계좌 ID, 송금할 금액 |
| 실행 Context | 프로그램이 Agent 실행 시 전달 | 접근 가능한 계좌, 승인된 요청 ID |

State는 Agent가 작업하며 갱신하는 정보(대화 기록 등)이고, Context는 프로그램이 실행 시점에 주입하는 신뢰할 수 있는 기준값(사용자 권한 등)이다. `agent.invoke(..., context=execution_context)`로 전달하고, Middleware에서는 `request.runtime.context`로 읽는다. **LLM이 만들어내는 인자와, 프로그램이 보증하는 Context를 분리**해야 "모델이 그렇게 말했으니까" 식의 권한 우회를 막을 수 있다.

## 실행 전 검증 — 인자·권한·승인

```python
def validate_proposal(proposal: dict, context: dict):
    if context['cancelled']:
        return {'status': 'cancelled', ...}
    schema = TOOL_SCHEMAS.get(proposal['name'])
    if schema is None:
        return failure('UNKNOWN_TOOL', ...)
    try:
        args = schema.model_validate(proposal['args'])   # Pydantic으로 형식·범위 검증
    except ValidationError:
        return failure('INVALID_ARGUMENT', ...)
    if args.account_id not in context['allowed_accounts']:
        return failure('FORBIDDEN', ...)
    if proposal['name'] == 'transfer':
        if args.amount > MAX_TRANSFER:
            return failure('LIMIT_EXCEEDED', ...)
        if args.request_id in context['rejected_request_ids']:
            return {'status': 'cancelled', 'code': 'APPROVAL_REJECTED', ...}
        if args.request_id not in context['approved_request_ids']:
            return {'status': 'waiting_for_human', 'code': 'APPROVAL_REQUIRED', ...}
    return args   # 검증된 Pydantic 객체 (통과)
```

검사는 이름 → 인자 형식(Pydantic `model_validate`) → 계좌 접근 권한 → (송금이면) 한도·승인 순서로 계단식으로 진행하고, 딕셔너리(실패)와 Pydantic 객체(통과)로 결과 형태 자체를 구분한다. 중요한 건 **모델이 인자에 `"approved": True`를 끼워 넣어도 무시**된다는 점이다 — 승인 여부는 인자가 아니라 Context의 `approved_request_ids`(프로그램이 관리하는 값)로만 판단한다.

이 검증을 `wrap_tool_call`로 감싸면:

```python
@wrap_tool_call
def validate_tool_call(request: ToolCallRequest, handler):
    result = validate_proposal(request.tool_call, request.runtime.context)
    if isinstance(result, dict):     # 거절·취소·승인대기
        return ToolMessage(content=json.dumps(result, ensure_ascii=False),
                            tool_call_id=request.tool_call["id"], status="error")
    return handler(request)          # 통과해야만 실제 Tool 실행
```

거절되면 `handler`를 호출하지 않으므로 Tool 자체는 절대 실행되지 않고, 사유가 담긴 `ToolMessage`가 LLM에 돌아가 사용자에게 설명할 소재가 된다.

## 실행 후 결과 검증

Tool이 외부 API처럼 반환값을 보장하기 어려운 경우, `handler(request)`로 **일단 실행한 뒤** 반환된 `ToolMessage`를 검사해서 LLM에 전달되기 전에 걸러낼 수 있다.

```python
@wrap_tool_call
def validate_tool_result(request: ToolCallRequest, handler):
    message = handler(request)                 # 먼저 실행
    if request.tool_call["name"] != "lookup_account" or message.status == "error":
        return message
    try:
        response = LookupResponse.model_validate_json(message.content)
    except ValidationError:
        error = failure("INVALID_TOOL_RESULT", ...)
    else:
        if response.account_id != request.tool_call["args"]["account_id"]:
            error = failure("RESULT_MISMATCH", ...)   # 요청한 계좌와 반환된 계좌가 다름
    return ToolMessage(content=json.dumps(error, ...), status="error") if error else message
```

`middleware=[force_tool_call, validate_tool_call, validate_tool_result]` 순서로 등록하면 `validate_tool_call → validate_tool_result → Tool` 순으로 호출이 들어가고, 결과는 반대 순서로 되짚어 나온다. 실행 전 검사가 이미 거절했다면 `handler`가 호출되지 않으므로 Tool 실행도, 결과 검증도 아예 일어나지 않는다.

## 호출 횟수 제한

`ToolCallLimitMiddleware`는 Tool 호출 횟수를 관리하는 내장 Middleware다.

```python
ToolCallLimitMiddleware(run_limit=0, exit_behavior="continue")       # 전체 Tool 호출 한도
ToolCallLimitMiddleware(tool_name="lookup_account", run_limit=2)     # 특정 Tool만 한도
```

한도를 넘긴 호출에는 Tool 실행 없이 오류 메시지가 반환되고, `exit_behavior="continue"`면 모델이 그 결과를 받아 사용자에게 안내할 수 있다. 호출 횟수는 Agent를 새로 `invoke`할 때마다 초기화된다.

## 검사 위치 정리

| 검사 | 실행 시점 | 적용 방식 |
|---|---|---|
| 인자·권한·승인 | Tool 실행 전 | `@wrap_tool_call`에서 `handler(request)` 호출 전에 검사 |
| 반환값 | Tool 실행 후, LLM 전달 전 | `@wrap_tool_call`에서 `handler(request)`가 반환한 결과 검사 |
| 호출 횟수 | 허용 횟수를 넘긴 호출의 실행 전 | `ToolCallLimitMiddleware` |

검증 함수는 "무엇을 검사할지"를 정의하고, Middleware는 "언제 그 검사를 끼워 넣을지"를 연결한다. Tool이 많아지면 `validate_proposal`처럼 하나의 함수에서 이름으로 분기하는 대신, Tool별 검증 함수를 `TOOL_GUARDS = {"lookup_account": validate_lookup, "transfer": validate_transfer}`처럼 매핑해두고 공통 Middleware에서 이름으로 찾아 호출하는 방식으로 확장할 수 있다.

## 실습: Context로 Tool 실행 허용하기

`{"allow_tool": True/False}` Context만으로 같은 Tool 호출을 허용·차단하는 Middleware를 구현했다. `allow_tool`이 `False`면 `handler`를 호출하지 않고 "실행 불가 함수입니다" `ToolMessage`를 바로 반환하고, `True`면 실제 Tool을 실행한다 — 계좌 예제의 복잡한 검증 로직을 걷어내면 결국 Tool 통제의 핵심은 "Context를 보고 `handler`를 호출할지 말지 정하는 것" 하나로 요약된다는 걸 보여주는 최소 예제다.
