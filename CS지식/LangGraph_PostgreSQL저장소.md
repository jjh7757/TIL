# LangGraph PostgreSQL 저장소 — Checkpointer와 Store를 DB에 영속화하기

[메모리와 상태](LangGraph_메모리와상태.md)에서 `MemorySaver`(인메모리)로 익힌 Checkpointer/Store를 PostgreSQL로 바꿔, 커널을 재시작해도 대화와 프로필이 남도록 만든 실습이다.

## 준비

```bash
pip install langgraph-checkpoint-postgres "psycopg[binary]"
```

- 실습용 DB를 먼저 만든다: `CREATE DATABASE langgraph_prac;`
- 접속 정보는 `.env`에 개별 변수(`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`)로 두고, 코드에서 `urllib.parse.quote`로 인코딩해 `postgresql://사용자:비밀번호@localhost:5432/DB명` URI를 조립한다. 비밀번호에 `@`, `:` 같은 특수문자가 있어도 URI가 깨지지 않게 하려는 처리다.

## 연결 옵션

```python
conn = psycopg.connect(
    DB_URI,
    autocommit=True,       # 변경 사항 즉시 반영
    prepare_threshold=0,   # 첫 실행부터 준비된 쿼리 사용
    row_factory=dict_row,  # 조회 결과를 딕셔너리로 반환
)
checkpointer = PostgresSaver(conn)
checkpointer.setup()       # 체크포인트 테이블 생성
```

- `autocommit=True`는 노트북 주석대로 "변경 사항 즉시 반영"하려는 설정이다. 꺼 두면 커밋 전까지 다른 연결(예: SQL 도구)에서 저장 내용이 보이지 않을 수 있다.
- Checkpointer용 연결(`conn`)과 Store용 연결(`store_conn`)은 따로 만들고, 한 번 만든 객체를 이후 셀에서 재사용한다.

## 자동 생성되는 테이블

`setup()`을 호출하면 `PostgresSaver`와 `PostgresStore`가 자기 테이블을 알아서 만든다. 같은 DB를 쓰지만 테이블은 별개다.

| 저장소 | 테이블 | 역할 |
|---|---|---|
| Checkpointer | `checkpoints` | 체크포인트 상태 정보와 메타데이터 |
| | `checkpoint_blobs` | 메시지 목록 등 State 값의 직렬화 데이터 |
| | `checkpoint_writes` | 노드 실행 중 중간 결과 (복구용) |
| | `checkpoint_migrations` | 스키마 변경 이력 |
| Store | `store` | namespace/key별 JSON 데이터 |
| | `store_migrations` | 스키마 변경 이력 |

테이블 구조는 직접 `\d`로 확인했다.

```
checkpoints:  thread_id TEXT, checkpoint_ns TEXT, checkpoint_id TEXT,
              parent_checkpoint_id TEXT, type TEXT, checkpoint JSONB, metadata JSONB
              PK (thread_id, checkpoint_ns, checkpoint_id)

store:        prefix TEXT, key TEXT, value JSONB, created_at, updated_at, expires_at, ttl_minutes
              PK (prefix, key)
```

SQL은 **저장 내용을 확인하는 용도**로만 쓰고, 저장·수정은 Checkpointer/Store 메서드로 한다. 테이블 내용은 라이브러리 내부 직렬화 형식이라 SQL로 직접 고치면 깨질 수 있다.

## Checkpointer: 대화 저장과 복원

```python
graph = create_agent(model=llm, tools=[], system_prompt="...", checkpointer=checkpointer)
config = {"configurable": {"thread_id": "postgres-chat-demo2"}}

graph.invoke({"messages": [("human", "내 이름은 민수야.")]}, config=config)
graph.invoke({"messages": [("human", "내 이름 알려줘.")]}, config=config)  # 이전 대화를 참고해 답함
graph.get_state(config).values["messages"]                              # DB에서 State 조회
```

- 커널을 재시작해도 **같은 `thread_id`**로 `get_state`/`invoke`하면 대화가 복원된다. 메모리 구현체(`MemorySaver`)와의 가장 큰 차이다.
- 새 `thread_id`를 쓰면 빈 State에서 시작한다.

## Store: 사용자 프로필

```python
store = PostgresStore(store_conn)
store.setup()

store.put(("users", "user-001"), "profile", {"name": "철수", "interest": "Python"})
item = store.get(("users", "user-001"), "profile")   # Item | None
item.value                                            # {'name': '철수', 'interest': 'Python'}
```

- 같은 namespace와 key로 다시 `put`하면 갱신(upsert)된다.
- namespace 튜플은 `store.prefix` 컬럼에 `.`으로 이어 붙여 저장된다: `("users", "user-001")` → `users.user-001`. 그래서 아래 SQL과 `store.get`이 같은 행을 가리킨다.

```sql
SELECT * FROM store WHERE prefix = 'users.user-001' AND key = 'profile';
```

### `store.get`은 딕셔너리의 `get`과 다르다

| | `dict.get(key, default)` | `store.get(namespace, key)` |
|---|---|---|
| 대상 | 메모리의 딕셔너리 | 저장소(DB) |
| 없을 때 | `default` (생략하면 `None`) | `None` (기본값 인자 없음) |
| 반환값 | 값 그 자체 | `Item` 객체 → `.value`로 꺼냄 |

그래서 노드 안에서는 `profile.value["name"]`처럼 쓰고, 없을 때를 대비해 `if profile:`로 분기한다.

## 두 저장소를 함께 쓰기

```python
profile_graph = builder.compile(checkpointer=checkpointer, store=store)
config = {"configurable": {"thread_id": "postgres-profile-chat", "user_id": "user-001"}}
```

노드 함수는 매개변수 이름(`state`, `config`, `store`)으로 필요한 것을 주입받는다.

| 정보 | 저장 위치 | 새 `thread_id`로 바꾸면 |
|---|---|---|
| 이름·관심 분야 | Store (`user_id`) | **유지됨** |
| "나는 등산을 좋아해" (대화 중 한 말) | Checkpointer (`thread_id`) | **사라짐** (새 스레드 State는 비어 있음) |

노트북은 기존 스레드와 새 스레드에 같은 질문("이름, 관심 분야, 취미를 알려줘")을 던져 이 차이를 확인하게 한다. 기대 결과는 기존 스레드는 취미까지 답하고, 새 스레드는 이름·관심 분야만 알고 취미는 모른다고 답하는 것이다.

마지막에는 `conn.close()`, `store_conn.close()`로 연결을 닫는다. 연결은 끊겨도 DB에 저장된 데이터는 남는다.

## 개인 실습: 두 저장소를 외래키로 연결해 보기

`checkpoints`에 `user_data`(사용자 테이블)를 외래키로 연결하다가 알게 된 점들.

1. **`thread_id`에 직접 FK를 걸 수 없다.** `checkpoints.thread_id`는 LangGraph가 쓰는 임의 문자열(`postgres-chat-demo3` 등)이라 `user_data.id`(`'1'`, `'2'`)와 값이 맞지 않는다. 이미 데이터가 있는 상태에서 FK를 추가하면 제약 검사에서 실패한다. → 별도 컬럼(`user_id`)을 추가해 그 컬럼에 FK를 걸었다. 새 컬럼은 NULL을 허용하므로 기존 행은 영향이 없다.

   ```sql
   ALTER TABLE checkpoints
       ADD COLUMN user_id VARCHAR(7),
       ADD CONSTRAINT fk_checkpoints_user FOREIGN KEY (user_id) REFERENCES user_data (id);
   ```

2. **LangGraph는 이 컬럼을 채워 주지 않는다.** 체크포인트를 저장할 때는 우리가 추가한 `user_id`를 모르므로, 연결하려면 저장 후 `UPDATE`를 따로 해야 한다.

3. **`store`를 가리키려면 컬럼이 두 개 필요하다.** `store`의 PK가 `(prefix, key)` 복합키이고, FK는 참조 대상의 PK/UNIQUE와 컬럼 구성이 같아야 한다.

   ```sql
   ALTER TABLE checkpoints
       ADD COLUMN store_prefix TEXT,
       ADD COLUMN store_key    TEXT,
       ADD CONSTRAINT fk_checkpoints_store
           FOREIGN KEY (store_prefix, store_key) REFERENCES store (prefix, key)
           ON DELETE SET NULL;
   ```

   `ON DELETE SET NULL`을 붙인 이유: `store` 행은 삭제되거나 TTL로 만료될 수 있는데, 이 옵션이 없으면 참조하는 체크포인트가 있을 때 삭제가 막힌다.

4. **복합키 조인은 `ON`에 두 컬럼을 모두 건다.** 한 컬럼만 걸면 같은 `prefix`의 다른 `key` 행이 섞여 중복 행이 생긴다.

   ```sql
   SELECT c.thread_id, s.value->>'name' AS name
   FROM checkpoints c
   JOIN store s ON s.prefix = c.store_prefix AND s.key = c.store_key;
   ```

5. **`user`는 예약어다.** `ON user.id = ...`처럼 테이블 별칭 없이 `user`를 쓰면 현재 DB 사용자로 해석돼 오류가 난다. 테이블 이름(`user_data`)이나 별칭을 써야 한다.

> 라이브러리가 관리하는 테이블에 컬럼과 FK를 직접 붙이는 건 실습용이다. 라이브러리 업그레이드 시 마이그레이션과 충돌할 수 있어, 실제 서비스에서는 사용자-스레드 대응표를 **별도 테이블**로 두는 편이 안전하다.
