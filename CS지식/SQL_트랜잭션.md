# SQL 트랜잭션 실습

하나 이상의 SQL 작업을 하나로 묶는 트랜잭션을 계좌 이체 예제로 직접 실행해 보고, 확정(`COMMIT`)·취소(`ROLLBACK`)·오류 시 동작과 백엔드(Python) 처리 패턴을 정리했습니다.
트랜잭션 개념과 명령어 분류는 [SQL 기초: DDL과 DML](SQL기초_DDL_DML.md)에 있습니다.

> PostgreSQL 기준.

## 트랜잭션이란

하나 이상의 SQL 작업을 하나로 묶은 **논리적 작업 단위**다.

- 김철수가 이영희에게 30,000원을 송금하려면 김철수 계좌에서 출금하고 이영희 계좌에 입금해야 한다.
- 두 작업을 한 트랜잭션으로 묶으면 **모두 반영하거나 모두 취소**할 수 있어, 출금만 반영되고 입금은 안 된 상태를 막는다.

| 명령어 | 역할 |
|--------|------|
| `BEGIN` | 트랜잭션 시작 |
| `COMMIT` | 현재 트랜잭션의 변경을 **확정**하고 종료 |
| `ROLLBACK` | 현재 트랜잭션의 변경을 **취소**하고 종료 |

- 성공하면 `COMMIT`, 실패하거나 취소하려면 `ROLLBACK`으로 종료한다.
- 종료하지 않으면 변경이 미확정 상태로 남고, **잠금** 때문에 다른 작업이 기다릴 수 있다.
- `COMMIT`으로 확정한 변경은 이후 `ROLLBACK`으로 되돌릴 수 없다.

## 실습 데이터 준비

같은 연결에서 위에서부터 순서대로 실행한다. 준비 SQL은 **자동 커밋**이 켜진 상태에서 실행한다. (자동 커밋: 명시적으로 트랜잭션을 시작하지 않으면 각 SQL 문이 성공할 때 바로 확정되는 방식)

```sql
CREATE TABLE transaction_account (
    account_id INTEGER PRIMARY KEY,
    owner_name VARCHAR(20) NOT NULL,
    balance INTEGER NOT NULL CHECK (balance >= 0)
);

INSERT INTO transaction_account (account_id, owner_name, balance)
VALUES
    (1, '김철수', 100000),
    (2, '이영희', 50000);
```

## 변경 확정하기 (COMMIT)

`BEGIN`부터 `COMMIT`까지 두 `UPDATE`를 하나로 묶는다.

```sql
BEGIN;

UPDATE transaction_account
SET balance = balance - 30000
WHERE account_id = 1;

UPDATE transaction_account
SET balance = balance + 30000
WHERE account_id = 2;

COMMIT;

SELECT * FROM transaction_account ORDER BY account_id;
```

- 확정 후 잔액: 김철수 **70,000원**, 이영희 **80,000원**.

## 변경 취소하기 (ROLLBACK)

김철수의 잔액을 10,000원 줄인 뒤 취소한다.

```sql
BEGIN;

UPDATE transaction_account
SET balance = balance - 10000
WHERE account_id = 1;

SELECT * FROM transaction_account ORDER BY account_id;   -- 김철수 60,000원

ROLLBACK;

SELECT * FROM transaction_account ORDER BY account_id;   -- 김철수 70,000원
```

- **같은 트랜잭션 안에서는** 아직 확정하지 않은 자기 변경을 조회할 수 있다. (ROLLBACK 전 60,000원)
- ROLLBACK 후에는 70,000원으로 돌아온다. 앞서 확정한 송금은 유지된다.

## 오류가 발생한 경우

아래 SQL은 **명령문별로** 실행한다. 두 번째 `UPDATE`에서 의도적으로 오류를 낸다.

```sql
BEGIN;

UPDATE transaction_account
SET balance = balance + 10000
WHERE account_id = 2;            -- 성공

UPDATE transaction_account
SET balance = balance - 1000000
WHERE account_id = 1;            -- 잔액이 음수 → CHECK 제약조건 위반
```

- 70,000원에서 100만 원을 출금하려 하므로 `CHECK (balance >= 0)`을 위반해 오류가 난다.
- 오류가 난 트랜잭션은 이어서 실행할 수 없으니 별도로 전체를 취소한다.

```sql
ROLLBACK;

SELECT * FROM transaction_account ORDER BY account_id;
```

- 먼저 성공했던 **이영희의 +10,000원도 함께 취소**되어 김철수 70,000원, 이영희 80,000원이 유지된다. 이것이 "모두 반영하거나 모두 취소"다.

## 백엔드에서 오류 처리하기

작업이 모두 성공하면 `COMMIT`, 도중에 예외가 나면 `ROLLBACK`한다. `connection`은 연결된 DB 객체이고, 진행 중인 트랜잭션이 없는 상태에서 시작한다고 가정한다.

```python
cursor = connection.cursor()

try:
    cursor.execute("BEGIN")

    cursor.execute("""
        UPDATE transaction_account
        SET balance = balance - 30000
        WHERE account_id = 1
    """)

    cursor.execute("""
        UPDATE transaction_account
        SET balance = balance + 30000
        WHERE account_id = 2
    """)

    connection.commit()
except Exception:
    connection.rollback()
    raise
finally:
    cursor.close()
```

- SQL 실행 중 오류가 나면 앞서 실행한 변경도 함께 취소된다.
- `raise`는 예외를 다시 던져 요청을 처리하는 쪽이 **실패를 알 수 있게** 한다. 롤백만 하고 삼키면 호출자는 성공한 줄 안다.
- `finally`의 `cursor.close()`는 성공·실패와 상관없이 항상 실행된다.

## 사용 시 확인할 점

- **함께 성공하거나 함께 취소되어야 하는 작업**을 하나의 트랜잭션으로 묶는다.
- 시작한 트랜잭션은 작업이 끝나면 **바로 종료**한다. 오래 열어 두면 다른 작업이 잠금 해제를 기다린다.
