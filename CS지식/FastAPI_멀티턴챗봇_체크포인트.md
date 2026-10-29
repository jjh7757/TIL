# 멀티턴 챗봇과 체크포인트

같은 채팅방에서 질문을 이어 가고, **서버를 재시작해도 대화 맥락을 복원**하는 챗봇을 구성합니다. 화면에 표시할 **질문·답변**과 Agent가 사용할 **실행 상태**를 따로 저장하는 것이 핵심입니다. ([RAG 스트리밍](FastAPI_RAG스트리밍_SSE.md)의 단발 질문과 달리 이전 대화를 기억)

## 대화 상태 저장

### 체크포인트와 체크포인터

- **체크포인트**: 그래프 실행의 **특정 시점 상태**를 저장한 것. 사용자 메시지·최종 답변뿐 아니라 **도구 호출·결과, 다음에 실행할 작업 정보**도 포함. 질문 한 번을 처리하는 동안에도 여러 개가 만들어진다
- **체크포인터**: 이 상태를 저장하고 다시 읽는 객체. Agent에 연결해 같은 대화의 상태를 불러와 후속 질문을 처리

이 앱은 프로세스가 종료되어도 상태가 남도록 PostgreSQL에 저장하는 **`AsyncPostgresSaver`** 를 사용합니다. (메모리 체크포인터 `InMemorySaver`는 재시작하면 사라짐)

### 화면 기록과 Agent 상태를 나누는 이유

**대화 기록을 보존하는 일**과 **LLM에 넣을 컨텍스트를 구성하는 일**은 목적이 다릅니다.

| 구분 | 내용 |
|------|------|
| 화면용 대화 기록 | 사용자가 주고받은 질문과 최종 답변의 **원문**. 다시 읽을 수 있게 시간순 저장 |
| Agent 상태 | 대화를 이어 가고 실행을 재개하는 데 필요한 데이터. 화면에 안 보이는 **도구 호출·결과**, 다음 실행 정보 포함 |
| LLM 컨텍스트 | **이번 모델 호출에 실제로 넣는 입력**. 시스템 지시문, 이전 메시지, 새 질문, 도구 결과 등. Agent 상태를 바탕으로 구성하지만 체크포인트 전체를 보내지는 않음 |

대화가 길어지면 전체 기록을 매번 LLM에 넣을 때 **컨텍스트 길이 제한, 토큰 비용, 응답 시간** 문제가 생깁니다. 오래된 대화를 요약하거나 필요한 메시지만 골라 **모델 입력을 줄일** 수 있는데, 이때 사용자가 다시 읽을 원문까지 줄일 필요는 없습니다.

- 화면용 기록엔 질문·답변 100개를 그대로 두고, LLM엔 **요약 + 최근 메시지 + 필요한 도구 결과**만 전달 가능
- 기록을 따로 저장하므로 Agent 메시지 상태를 요약으로 바꿔도 화면은 원문 유지
- 반대로 Agent는 최종 답변에 드러나지 않은 **도구 결과**를 후속 질문에 활용 가능

| 저장 위치 | 저장 내용 | 용도 |
|-----------|-----------|------|
| `chat_rooms` | 소유자·제목, **확정한 `checkpoint_id`** | 채팅방 관리, 다음 대화의 시작점 |
| `chat_messages` | 사용자 질문과 최종 답변 원문 | 기록 보존, 화면 표시 |
| 체크포인트 테이블 | 메시지, 도구 호출·결과, 그래프 실행 상태 | Agent 실행 상태·대화 맥락 복원 |

```
ChatService ─┬─▶ ChatRepository ──▶ chat_rooms / chat_messages   (SQLAlchemy 연결·트랜잭션)
             └─▶ 챗봇 Agent ──▶ AsyncPostgresSaver ──▶ 체크포인트 테이블   (psycopg 별도 연결)
```

> 같은 PostgreSQL DB를 써도 **연결과 트랜잭션이 별개**다. 화면 기록 저장이 실패해도 체크포인트 저장은 자동으로 취소되지 않는다.

### `thread_id`와 `checkpoint_id`

| 값 | 의미 | 쓰는 이유 |
|----|------|-----------|
| `thread_id` | 체크포인트를 묶는 **대화** 식별자 | 채팅방끼리 맥락이 섞이지 않게 |
| `checkpoint_id` | 한 대화 안의 **특정 시점** 식별자 | 화면 기록과 함께 저장에 성공한 시점에서 다음 대화를 시작 |

- `ChatRoom.thread_id`는 `chat:{room.id}` → 같은 방은 항상 같은 값, 방마다 다른 값
- 클라이언트는 **방 ID와 새 질문만** 보낸다. 서버가 방 소유권을 확인한 뒤 `thread_id`·`checkpoint_id`를 정한다
- **`thread_id` 자체에는 접근 권한 검사 기능이 없다** → 클라이언트가 `thread_id`를 직접 보내게 하면 남의 대화를 불러올 수 있으므로 권한은 방 소유권으로 확인

## PostgreSQL 체크포인터 연결

### lifespan에서 연결 유지

```python
# main.py lifespan 내부의 체크포인터 초기화
checkpoint_url = make_url(get_settings().database_url).set(drivername="postgresql")
async with AsyncPostgresSaver.from_conn_string(
    checkpoint_url.render_as_string(hide_password=False)
) as checkpointer:
    await checkpointer.setup()                       # 체크포인트 테이블 생성·마이그레이션
    app.state.chat_agent = create_chat_agent(checkpointer)
    yield
```

| 부분 | 이유 |
|------|------|
| `.set(drivername="postgresql")` | `AsyncPostgresSaver`는 psycopg를 직접 사용 → SQLAlchemy 전용 표기 `postgresql+psycopg://`를 일반 `postgresql://`로 변환 |
| `render_as_string(hide_password=False)` | `str(url)`은 비밀번호를 `***`로 가림 → 실제 접속 문자열이 필요 |
| `await checkpointer.setup()` | 체크포인트 테이블을 만들고 버전을 맞춤 (Alembic이 아닌 체크포인터가 관리) |
| `yield`를 `async with` **안에** | 요청 처리 중에는 연결이 열려 있고, 앱 종료로 블록을 벗어나면 정리 |

### Alembic에서 체크포인트 테이블 제외

서비스 테이블은 **Alembic**, 체크포인트 테이블은 **`checkpointer.setup()`** 이 관리합니다. 체크포인트 테이블은 `Base.metadata`에 없으므로, 제외하지 않으면 autogenerate가 "모델에 없는 테이블"로 보고 **삭제 코드를 생성**합니다.

```python
# alembic/env.py
def include_name(name, type_, parent_names):
    checkpoint_tables = {
        "checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations"
    }
    return type_ != "table" or name not in checkpoint_tables
```

`False`를 반환한 대상이 변경 감지에서 빠집니다 → 체크포인트 테이블만 `False`, 나머지는 `True`. ([비동기 설정과 Alembic](FastAPI_비동기설정_Alembic.md) 참고)

---

## 화면용 대화 기록 조회 — 커서 기반 페이지네이션

채팅방을 열면 **최근 대화부터** 보여 주고, 요청할 때 더 오래된 기록을 불러옵니다.

| 방식 | 기준 | 특징 |
|------|------|------|
| 오프셋 | "앞에서 N개 건너뛰기" (`OFFSET`) | 새 메시지가 추가되면 위치가 밀려 **중복·누락** 가능. 뒤로 갈수록 건너뛸 행이 많아 느려짐 |
| **커서** | "이 ID보다 이전" (`id < cursor`) | 새 메시지가 추가돼도 기준 ID가 밀리지 않음. **ID가 연속일 필요 없음** |

| 값 | 방향 | 의미 |
|----|------|------|
| `limit` | 요청 | 한 번에 받을 최대 개수 |
| `cursor` | 요청 | 이 ID보다 작은 메시지 조회. 첫 요청엔 생략 |
| `items` | 응답 | 조회한 메시지를 **오래된 순**으로 |
| `next_cursor` | 응답 | 다음 요청의 `cursor`. 더 없으면 `null` |
| `has_more` | 응답 | 더 가져올 과거 기록 여부 |

### Repository — `limit + 1`개 조회

```python
statement = select(ChatMessage).where(ChatMessage.room_id == room_id)
if cursor is not None:
    statement = statement.where(ChatMessage.id < cursor)
result = await db.scalars(
    statement.order_by(ChatMessage.id.desc()).limit(limit + 1)
)
return result.all()
```

**1개를 더 읽어** 다음 페이지가 있는지 판단합니다. `limit=3`에서 4개가 나오면 3개만 응답하고 `has_more=true`. 더 읽은 1개는 다음 요청에서 다시 조회됩니다. (별도의 `COUNT` 쿼리가 필요 없음)

### Service — 고르고 뒤집기

```python
has_more = len(rows) > params.limit
page = rows[:params.limit]
return MessagePageResponse(
    items=[MessageResponse.model_validate(m) for m in reversed(page)],
    next_cursor=page[-1].id if has_more else None,
    has_more=has_more,
)
```

- DB는 **최신순**으로 가져오지만 화면은 **오래된 순**으로 읽어야 하므로 `reversed(page)`
- `next_cursor`는 뒤집기 **전** `page[-1].id` = 이번 응답의 **가장 오래된** 메시지 ID
- 다음 요청이 `< cursor`라 경계 메시지가 중복되지 않는다

예시: ID 115~120, `limit=3`

| 요청 | DB 조회 순서 | 응답 `items` | `next_cursor` | `has_more` |
|------|--------------|--------------|---------------|------------|
| `?limit=3` | 120, 119, 118, 117 | 118, 119, 120 | 118 | true |
| `?limit=3&cursor=118` | 117, 116, 115 | 115, 116, 117 | null | false |

화면의 "이전 메시지 불러오기"는 `next_cursor`로 조회해 **현재 목록 앞에** 붙이고(115~117 + 118~120), `has_more`가 false이면 버튼을 숨깁니다.

---

## 대화 실행과 상태 확정

### 채팅방 생애 주기

| 시점 | API | 서버가 생성·저장하는 것 |
|------|-----|------------------------|
| 새 채팅 | `POST /chat/rooms` `{"title": "새 채팅"}` | 방 ID·`thread_id` 결정, **빈 체크포인트 생성**, 그 ID를 포함해 `chat_rooms`에 저장 |
| 방 열기 | `GET /chat/rooms/{room_id}`, `GET .../messages?limit=30` | 방 정보·화면용 메시지 조회. **Agent 실행 안 함** |
| 입력 중 | 요청 없음 | 화면에서만 관리 |
| 질문 전송 | `POST /chat/rooms/{room_id}/messages/stream` `{"content": "질문"}` | 방의 체크포인트에서 Agent 실행. 단계마다 체크포인트 저장, 답변 조각·도구 이벤트 전송 |
| 생성 완료 | 같은 요청 안 | 질문·답변을 `chat_messages`에 저장 + 방의 `checkpoint_id` 갱신 → **같은 SQLAlchemy 트랜잭션으로 커밋** |
| 저장 완료 | 같은 연결의 `done` | 저장된 질문·답변 반환, 화면은 임시 메시지를 교체 |

저장 후 화면은 `GET /chat/rooms`로 목록을 갱신하고, 후속 질문은 같은 방의 스트리밍 API로 보냅니다.

### 구현할 때 구분할 것

- **체크포인트와 화면 메시지의 저장은 별개**: 체크포인터는 실행 **중**, 화면 메시지는 최종 답변 **후** 저장. 트랜잭션이 달라 화면 저장이 실패해도 체크포인트는 남을 수 있다
- **빈 체크포인트 = 첫 질문이 실패했을 때의 시작점**: 방을 만들 때 모델을 호출하거나 빈 메시지 행을 만드는 게 아니다. 첫 질문의 기록 저장이 실패하면 `checkpoint_id`를 초기 값으로 유지 → 다음 질문이 **화면에 없는 대화 상태를 이어받지 않게**
- **질문 한 번에 전송 API 하나**: 일반 JSON용 `POST .../messages`와 스트리밍용 `.../messages/stream`은 둘 다 실행·저장을 하므로 연달아 호출하지 않는다
- **화면에 답변이 보이는 것 ≠ 저장 완료**: 저장 완료는 **커밋 후 보내는 `done`** 으로 확인. 연결이 끊겨 불확실하면 메시지 조회 API로 실제 결과 확인

### 확정한 상태에서 새 질문 실행

```python
config = {
    "configurable": {
        "thread_id": room.thread_id,
        "checkpoint_id": room.checkpoint_id,
    }
}
inputs = {"messages": [{"role": "user", "content": content}]}
result = await self.agent.ainvoke(inputs, config=config)
```

- `inputs`: 대화에 **추가할** 메시지, `config`: 복원할 상태의 **위치**
- Agent가 지정한 체크포인트의 메시지·도구 결과를 복원한 뒤 새 메시지를 추가 → 화면 기록 전체를 다시 보낼 필요 없음
- `thread_id`만 주면 **최신** 체크포인트를 불러온다. 최신 상태에는 **실패한 실행의 중간 기록**이 남아 있을 수 있으므로 방에 확정한 `checkpoint_id`를 함께 지정

## 같은 방의 요청 순서 보장 — 행 잠금

**트랜잭션**은 여러 DB 작업을 묶어 성공 시 커밋, 실패 시 롤백합니다. 여기서는 `async with db.begin()`으로 질문·답변 저장과 `checkpoint_id` 변경을 묶습니다. 하지만 트랜잭션을 시작했다고 **읽은 데이터를 독점하는 것은 아닙니다**. 여러 요청이 같은 값을 읽고 각자 작업할 수 있으며, 이를 제어하는 것이 **잠금(lock)** 입니다. 이 앱은 채팅방 행에 거는 **행 단위 잠금**을 씁니다.

### 잠금이 없으면 생기는 문제 (lost update)

| 시점 | 요청 A | 요청 B | 방의 `checkpoint_id` |
|------|--------|--------|---------------------|
| 시작 | cp-100에서 실행 | cp-100에서 다른 질문 실행 | cp-100 |
| A 완료 | A 답변 포함 cp-101 확정 | A 결과 모른 채 실행 중 | cp-101 |
| B 완료 | | B 답변 포함 cp-102 확정 | cp-102 |

화면엔 A·B의 질문·답변이 모두 있지만, 다음 대화가 쓸 **cp-102에는 A의 결과가 없습니다**. 그래서 대화 실행·제목 변경·삭제 시 채팅방 행에 잠금을 겁니다.

### `FOR UPDATE NOWAIT`

```python
# ChatRepository.find_room(lock=True)일 때
statement = statement.with_for_update(nowait=True)
```

- 조회 SQL에 `FOR UPDATE NOWAIT`를 붙인다 → 조회한 행의 잠금을 얻고 **현재 트랜잭션이 끝날 때까지** 유지
- 다른 트랜잭션이 같은 행을 수정·삭제하거나 `FOR UPDATE`로 잠그려 하면 충돌
- `FOR UPDATE`는 기본적으로 잠금이 풀릴 때까지 **기다린다**. `nowait=True`는 즉시 얻을 수 없으면 **바로 오류** (PostgreSQL `55P03 lock_not_available`)

| 처리 시점 | 트랜잭션·잠금 |
|-----------|---------------|
| 요청 시작 | `async with db.begin()` 트랜잭션 시작 |
| 방 조회 | 소유한 방을 `FOR UPDATE NOWAIT`로 조회 → 잠금 획득, `checkpoint_id` 읽기 |
| Agent 실행 | **잠금 유지한 채** 상태 복원·답변 생성 |
| 결과 저장 | 질문·답변 저장, `checkpoint_id` 변경 |
| 정상 종료 | 커밋 → 잠금 해제 |
| 예외 종료 | SQLAlchemy 트랜잭션 롤백 → 잠금 해제 |

- 잠금 대상은 `chat_rooms`의 **해당 방 행** 하나. 서로 다른 방은 독립적으로 잠긴다
- PostgreSQL 행 잠금은 **일반 `SELECT`를 막지 않으므로** 기록 조회는 가능
- 대화 실행·제목 변경·삭제가 모두 **같은 행의 잠금**을 얻도록 해 서로 겹치지 않게 한다
- 체크포인터의 **별도 트랜잭션까지 롤백되지는 않는다**
- 잠금 실패는 Service가 **409 `CHAT_ROOM_BUSY`** 로 변환

A가 처리 중이면 B는 Agent를 실행하지 않고 409를 받습니다. A가 cp-101을 확정한 뒤 B를 다시 보내면 B는 **A의 답변이 포함된 cp-101**에서 시작합니다. 이 구조는 동시 실행을 **막을** 뿐, 요청을 도착 순서대로 **대기열에 넣어 처리하지는 않습니다**.

> 트레이드오프: Agent 실행(LLM 호출) 내내 잠금과 **SQLAlchemy 연결 하나를 붙잡고** 있으므로, 동시에 대화 중인 방이 많으면 연결 풀이 빨리 소진될 수 있다.

---

## 도구 실행 상태 스트리밍

### `astream`의 `stream_mode` vs `astream_events`

둘 다 그래프를 비동기로 실행하며 중간 정보를 전달합니다. `astream()`은 **받을 데이터 종류**를 고르고, `astream_events(..., version="v2")`는 **모델·도구·그래프 내부의 실행 이벤트**를 받습니다.

| 호출 | 받는 정보 | 활용 |
|------|-----------|------|
| `astream(stream_mode="messages")` | 모델 메시지 조각·메타데이터 (도구 호출 인자 조각 포함 가능) | 답변 텍스트를 생성되는 대로 표시 |
| `astream(stream_mode="updates")` | 각 노드가 완료되어 반환한 상태 변경 | 도구 호출 요청, 도구 결과 `ToolMessage` 확인 |
| `astream(stream_mode="values")` | 각 단계 후의 **전체** 상태 | 누적 메시지 등 현재 상태 확인 |
| `astream(stream_mode="custom")` | 노드·도구가 **직접 내보낸** 데이터 | "문서 100개 중 30개 처리" 같은 진행률 |
| `astream_events(version="v2")` | 모델·도구 등의 **시작·스트리밍·종료** 이벤트 | 도구별 실행 시작·종료 + 답변 조각을 함께 표시 |

- `astream()`은 `stream_mode=["messages", "updates"]`처럼 여러 모드를 함께 지정 가능
- `astream_events`는 `event`, `name`, `run_id`, `data` 등이 담긴 dict를 반환 → `event` 값으로 구분
- `version="v2"`는 **이벤트 형식의 버전**이며 `stream_mode`와는 다른 설정

### 왜 `astream_events`인가

`updates`나 `messages`의 `tool_calls`는 **모델이 "도구를 실행하라"고 요청한 것**일 뿐, 실제 도구 실행이 시작·완료되었다는 알림이 아닙니다. 화면은 도구별로 **"조회 중 → 완료"** 를 보여 주므로:

- `on_tool_start` / `on_tool_end`로 **실제 실행 시점**을 받고
- 같은 `run_id`로 시작과 종료를 연결
- 도구 코드에 진행 알림을 추가하지 않아도 된다

도구 **내부의 처리 개수·진행률**까지 보여 주려면 도구 코드에서 `get_stream_writer()`로 데이터를 내보내고 `astream(stream_mode="custom")`으로 받는 방식이 적합합니다. 표시할 정보에 맞춰 **하나를 선택**합니다. 한 질문에 두 메서드를 각각 호출하면 **그래프도 두 번 실행**됩니다.

### SSE 이벤트로 변환

`POST /chat/rooms/{room_id}/messages/stream`은 `astream_events()`에서 필요한 이벤트만 골라 변환합니다.

| Agent 실행 이벤트 | Service 처리 |
|-------------------|--------------|
| `on_chat_model_start` | 답변 생성 중 `status` |
| `on_chat_model_stream` | 텍스트 조각 → `token` |
| `on_tool_start` | 도구 실행 ID·이름 → `tool_start` |
| `on_tool_end` | 도구 결과 상태에 따라 `tool_end` 또는 `tool_error` |
| 최상위 그래프의 `on_chain_end` | 저장할 최종 메시지 목록 `result` 확보 |
