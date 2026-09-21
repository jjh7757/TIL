# LangGraph 장애 허용 — 재시도, 재개, 멱등성

장애 허용(Fault Tolerance)은 장애가 발생했을 때 오류를 처리하거나 복구해서 작업을 계속하거나 재개할 수 있게 하는 능력이다.

## `RetryPolicy`로 노드 자동 재시도하기

노드에 `RetryPolicy`를 설정하면 지정한 오류가 발생했을 때 **한 번의 그래프 호출 안에서** 해당 노드만 자동으로 재시도한다.

| 설정 | 의미 |
|---|---|
| `initial_interval` | 첫 재시도 전 대기 시간 |
| `backoff_factor` | 대기 시간 증가 배수 |
| `max_interval` | 최대 대기 시간 |
| `max_attempts` | 최초 실행을 포함한 최대 시도 횟수 |
| `jitter` | 무작위 지연 적용 여부 |
| `retry_on` | 재시도할 예외 타입 또는 판별 함수 |

```python
retry_builder.add_node("call_service", call_unstable_service, retry_policy=retry_policy)
```

`prepare → call_service`로 연결하고 `call_service`가 두 번 실패한 뒤 성공하도록 구성하면, 실행 횟수는 `prepare=1`, `call_service=3`이 된다. **실패한 노드만 재시도되고, 이미 완료된 앞 노드는 다시 실행되지 않는다.** 재시도 횟수를 소진하면 `invoke()`에서 예외가 그대로 올라온다.

`retry_on`으로 지정하지 않은 예외(예: 형식 오류로 인한 `ValueError`)가 발생하면 재시도 없이 즉시 실패한다 — 같은 요청을 반복해도 해결되지 않는 오류를 재시도로 낭비하지 않기 위해서다. **노드가 예외를 던지지 않고 `{"status": "failed"}` 같은 값을 정상 반환하면 `RetryPolicy`는 아예 동작하지 않는다** — 재시도는 예외 기반이라는 걸 잊으면 "실패했는데 왜 재시도가 안 되지" 하는 함정에 빠진다.

| 방식 | 오류가 발생했을 때의 동작 |
|---|---|
| `RetryPolicy` | 노드 단위로 다시 실행한다. |
| `with_retry()` | Runnable 단위로 다시 실행한다. |
| `with_fallbacks()` | 지정한 다른 모델이나 체인으로 바꾸어 실행한다. |

재시도는 **실패할 가능성이 있고, 다시 실행할 필요가 있는 가장 작은 단위**에 건다. 노드 전체를 다시 돌려야 하면 `RetryPolicy`, 노드 안의 모델 호출만 다시 하면 되면 `model.with_retry()`를 쓴다.

## super-step과 checkpoint

super-step은 그래프에서 같은 차례에 실행되도록 예정된 노드들의 묶음이다. checkpointer를 설정하면 **각 super-step이 끝날 때마다** 그 시점까지의 State가 checkpoint로 저장된다.

```text
순차 실행: prepare → call_service → finish      (각 노드가 별도 super-step)
병렬 실행: prepare → [stable_branch, unstable_branch] → summarize  (대괄호 안은 같은 super-step)
```

순차 실행은 노드마다 super-step이 나뉘어 완료 즉시 checkpoint가 쌓이고, 병렬 실행은 같은 super-step의 노드가 모두 끝나야 checkpoint가 하나 생긴다.

## 노드 실행 실패와 재개

자동 재시도로도 해결이 안 돼 실행이 실패로 끝난 뒤, 원인을 고치고 이어서 처리하는 방법이다. 실패 원인을 해결한 다음 **같은 `thread_id`로 `invoke(None, config)`를 호출**하면 저장된 실행을 이어서 진행한다. `None`은 새 입력이 없다는 뜻이고, 재개할 노드는 `get_state(config).next`로 확인한다.

```python
try:
    sequential_graph.invoke({"request": "주문 확인"}, config)
except ConnectionError:
    ...
snapshot = sequential_graph.get_state(config)
print(snapshot.values, snapshot.next)   # {'prepared': ...}, ('call_service',)

sequential_gate["allow_service"] = True   # 문제 해결
sequential_graph.invoke(None, config)     # 실패한 노드부터 재개
```

완료된 `prepare`는 재실행되지 않고 실패했던 `call_service`만 처음부터 다시 실행된다.

재개는 **사용자**("다시 시도" 버튼)가 요청할 수도 있고, **자동**(실패를 기록해두고 일정 시간 뒤 백그라운드 worker가 재개)으로 이뤄질 수도 있다. 두 경우 모두 실제 재개는 같은 `thread_id`로 `invoke(None, config)`를 호출하는 것으로 시작한다. 예외 처리 코드 안에서 곧바로 대기 후 재개할 수도 있다:

```python
try:
    result = graph.invoke({"request": "..."}, config)
except ConnectionError:
    time.sleep(5)
    allow_service_gate["allow_service"] = True  # 복구 가정
    result = graph.invoke(None, config)
```

## 병렬 실행에서 일부만 실패하면

같은 super-step에서 두 노드 중 하나만 실패해도 **성공한 노드의 결과는 보존된다.**

```text
prepare
   ├─ stable_branch    ─ 성공 → 결과 보존
   └─ unstable_branch  ─ 실패 → 재개 시 이 노드만 다시 실행
```

`get_state(config)`의 `values`에는 성공한 `stable_result`가 이미 담겨 있고, `next`에는 실패한 `unstable_branch`만 표시된다. `snapshot.tasks`의 각 항목에서 `result`/`error`로 병렬 노드별 성공·실패를 확인할 수 있다. 원인을 해결하고 `invoke(None, config)`로 재개하면 `stable` 카운트는 그대로고 `unstable`만 한 번 더 실행된다 — 재개는 "실패 지점부터"이지 "그래프 전체를 처음부터"가 아니다.

| 구분 | 자동 재시도 | checkpoint 재개 |
|---|---|---|
| 실행 범위 | 한 노드를 다시 시도 | 저장된 그래프 실행을 이어서 진행 |
| 호출 코드에서 그래프를 다시 호출해야 하는가 | 아니요 | 예: `invoke(None, config)` |
| 설정 | `RetryPolicy` | checkpointer와 `thread_id` |

짧은 일시적 오류는 제한된 횟수만 자동 재시도하고, 그래도 실패하면 나중에 checkpoint에서 재개하는 식으로 **함께** 쓸 수 있다.

## 노드 실행 시간 제한하기

`TimeoutPolicy(run_timeout=...)`는 노드 한 번의 실행 시간을 제한하며 **비동기 노드에만** 적용된다. 시간을 넘기면 `NodeTimeoutError`가 발생하고, 이 예외를 `retry_on`으로 지정하면 재시도할 때마다 시간 제한이 새로 시작된다.

```python
timeout_builder.add_node(
    "slow_service", slow_service,
    timeout=TimeoutPolicy(run_timeout=2.0),
    retry_policy=RetryPolicy(max_attempts=2, retry_on=NodeTimeoutError, ...),
)
```

재시도해도 시간 초과가 계속되면 서비스 성격에 따라 실패 안내, 다른 모델로 대체, 또는 오래 걸리는 작업이면 백그라운드 worker에 맡기고 완료 시 알리는 방식으로 대응한다.

## 재시도 소진 후 직접 오류 처리하기

노드에 `error_handler`를 등록하면, `RetryPolicy`가 재시도 대상이 아니라고 판단하거나 재시도 횟수를 소진했을 때 이 함수가 실행된다. `error_handler(state, error: NodeError)`는 노드 이름과 예외를 담은 `NodeError`를 받아 `Command`로 State를 갱신하고 다음 노드로 이동시킬 수 있다.

```python
def service_error_handler(state, error: NodeError) -> Command:
    return Command(
        update={"status": "failed", "error_message": f"{error.node}: {error.error}"},
        goto="finalize",
    )

recovery_builder.add_node("call_service", failing_service, retry_policy=..., error_handler=service_error_handler)
```

재시도로도 복구가 안 되는 실패를 예외로 프로그램을 죽이는 대신, State에 실패 상태를 남기고 정상적인 종료 경로(`finalize`)로 흘려보낼 수 있다.

여러 노드에 같은 재시도·오류 처리 정책을 적용하려면 `builder.set_node_defaults(retry_policy=..., error_handler=...)`를 쓴다. 노드에 직접 지정한 값이 공통 설정보다 우선한다.

## 멱등성 — checkpoint가 되돌리지 못하는 것

DB 저장이나 메시지 전송처럼 **그래프 State 밖에도 흔적을 남기는 작업**(side effect)은, 저장이 끝난 뒤 응답을 받기 전에 노드가 실패해도 checkpoint가 그 외부 작업을 되돌려주지 않는다. 재개하면 실패한 노드는 처음부터 다시 실행되므로, 오류 이전에 이미 완료한 저장 코드도 다시 돌면서 중복 기록이 생길 수 있다.

**멱등성**은 같은 요청을 여러 번 처리해도 한 번 처리한 것과 같은 결과를 유지하는 성질이다. **멱등성 키**(예: `request_id`)로 이미 처리한 요청인지 확인해서 중복 저장을 막는다.

```python
def idempotent_save(state):
    request_id = state["request_id"]
    if request_id not in processed_request_ids:   # 이미 처리한 요청인지 먼저 확인
        external_rows.append({...})
        processed_request_ids.add(request_id)
    if not save_gate["allow_completion"]:
        raise ConnectionError("저장 후 응답을 받지 못했습니다.")
    return {"saved": True}
```

실패 직후와 재개 후 모두 외부 저장소의 기록 수는 `1`로 유지된다 — 노드가 두 번 실행돼도 외부 작업은 한 번만 실제로 반영된 것이다. 예제의 `set`/`list`는 한 프로세스 안에서만 중복을 막아주므로, 실제 서비스에서는 저장 결과와 처리 ID를 원자적으로 함께 기록하거나 외부 서비스가 제공하는 멱등성 키 기능을 사용해야 한다.

## 실습: 재시도 후 실패 결과 남기기

외부 조회 서비스에 연결 오류가 계속되는 상황에서, 세 번 재시도해도 실패하면 실패 사유를 State에 남기고 `finalize`로 이동해 정상 종료하는 그래프를 구현했다. `RetryPolicy(max_attempts=3, retry_on=ConnectionError)`와 `error_handler`를 같은 노드에 함께 등록하는 조합 — 재시도로 해결을 시도하되, 끝내 안 되면 예외를 밖으로 던지는 대신 상태로 흡수하는 패턴이다.
