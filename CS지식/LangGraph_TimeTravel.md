# LangGraph Time Travel — Checkpoint 조회, Replay, Fork

## Time Travel이란

Checkpointer를 연결한 그래프는 실행 중 State를 계속 checkpoint로 기록한다. Time Travel은 이 기록을 **조회**하고, 과거 시점부터 **다시 실행(Replay)**하거나, 과거 State를 **바꿔서 새 경로로 실행(Fork)**하는 기능이다.

| 동작 | 설명 |
|---|---|
| 조회 | 과거 checkpoint의 State와 다음 실행 노드를 확인 |
| Replay | 과거 값을 그대로 사용해 그 시점 이후를 다시 실행 |
| Fork | 과거 값을 수정한 뒤 다른 경로로 실행 |

[LangGraph 메모리와 상태](LangGraph_메모리와상태.md)에서 다룬 `get_state`/`get_state_history`가 여기서 그대로 확장된다 — Time Travel은 완전히 새로운 인프라가 아니라, 이미 있는 checkpoint 이력을 "조회만" 하던 걸 "그 지점부터 다시 실행"까지 하는 것이다.

## thread_id와 checkpoint_id는 다른 층위

`thread_id`가 하나의 실행 이력 전체를 가리킨다면, `checkpoint_id`는 그 이력 안의 **특정 시점**을 가리킨다.

```
thread_id: post-1
├── checkpoint_id: A  → 주제 정리 전
├── checkpoint_id: B  → 초안 작성 전
├── checkpoint_id: C  → 검토 전
└── checkpoint_id: D  → 실행 완료
```

각 snapshot의 `next`(다음에 실행할 노드)를 보고 원하는 시점을 찾는다 — `next == ('write_draft',)`인 snapshot을 찾으면 "초안 작성 직전"으로 돌아갈 수 있다. 과거 시점에서 실행하려면 `checkpoint_id`까지 포함된 그 snapshot의 `config`를 써야 한다(단순히 `thread_id`만 쓰면 항상 **최신** checkpoint를 가리킨다).

## Replay — 과거 값 그대로, 그 지점부터 다시

```python
replayed = graph.invoke(None, before_draft.config)
```

State를 안 바꾸고 `None`을 입력으로 넘기면, 이미 완료된 노드(`choose_topic`)는 재실행하지 않고 `next`에 있는 노드(`write_draft`)부터 실행한다. **같은 값을 써도 이후 노드의 코드는 다시 호출된다** — 즉 LLM 호출이 있는 노드라면 같은 프롬프트라도 다시 실제로 호출된다(캐시되는 게 아님).

Replay는 기존 checkpoint를 지우거나 덮어쓰지 않는다. 새 checkpoint가 같은 `thread_id` 이력에 계속 추가되고, 각 checkpoint는 자신이 이어진 이전 checkpoint를 `parent_config`로 가리킨다. 과거 B에서 Replay하면 새 checkpoint C'의 부모는 최신이었던 D가 아니라 **B**가 된다 — 이 부모 관계를 따라가면 실행 경로가 갈라진 걸 알 수 있다.

```
저장·조회 순서: A, B, C, D, C', D'
부모 관계:     A → B → C → D
                    └→ C' → D'
```

## Fork — 과거 값을 바꾼 뒤 다시

```python
fork_config = graph.update_state(
    config, {"draft": "수정된 초안"}, as_node="choose_topic",
)
forked = graph.invoke(None, fork_config)
```

`update_state()`로 과거 State의 일부를 바꾸면, 기존 checkpoint를 덮어쓰지 않고 **수정된 값을 담은 새 checkpoint**를 만든다. `as_node="choose_topic"`은 "이 값을 그 노드가 방금 작성한 것처럼 처리하라"는 뜻이라서, 다음 노드(`write_draft`)부터 이어진다.

Replay와의 차이: Fork에는 **수정된 State를 담는 checkpoint(U)가 하나 더 있다.**

```
저장·조회 순서: A, B, C, D, U, C', D'
부모 관계:     A → B → C → D
                    └→ U → C' → D'
                        ↑
                  update_state()
```

Fork 이후에도 기존 최신 결과(D)와 과거 checkpoint들은 전혀 바뀌지 않는다 — 완전히 별도 가지로 추가될 뿐이다.

## 실제 서비스에서는 이렇게 매핑된다

서비스 화면에는 `checkpoint`나 `Fork` 같은 용어를 직접 노출하지 않고, 사용자가 하는 "동작"으로 표현한다.

| UI 기능 | 내부 동작 |
|---|---|
| 다시 생성 | 선택한 checkpoint에서 Replay |
| 이 단계부터 다시 실행 | 선택한 checkpoint에서 Replay |
| 수정 후 계속 | 중간 결과 수정값을 State에 반영한 뒤 Fork |
| 이 버전에서 다시 작성 | 선택한 버전의 checkpoint에서 Fork |

**Replay 활용**: 장애 지점부터 재실행해 Agent 판단 과정 분석 / prompt·model·logic 수정 후 같은 과거 State로 결과 비교 / 앞의 비싼 검색·Tool 호출 결과는 유지한 채 이후 단계만 테스트.

**Fork 활용**: 사용자 수정 요청·검토자 피드백을 반영해 이후 작업 계속 / 같은 중간 State에 다른 조건을 적용해 결과 비교 / 긴 조사·분석 결과를 재사용해 여러 전략의 결과를 생성.

## 주의: State는 되감아도 외부 세계는 안 되감아진다

State는 과거 checkpoint에서 다시 실행할 수 있지만, **이미 보낸 메일이나 처리된 결제는 되돌아가지 않는다.** Replay/Fork로 이후 노드를 다시 실행하면 그 안의 외부 작업(API 호출, 메일 발송 등)도 다시 실행될 수 있으므로 중복 실행에 주의해야 한다 — [LangGraph Human-in-the-Loop](LangGraph_HumanInTheLoop.md)에서 "interrupt 이전 코드는 재실행돼도 안전해야 한다"고 정리했던 것과 같은 종류의 주의사항이, 여기서는 "그래프 재실행 시점 이후의 모든 외부 작업"으로 범위가 넓어진 것이다.
