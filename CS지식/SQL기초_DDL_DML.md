# SQL 기초: DDL과 DML

SQL의 기본 규칙, 명령어 분류(DDL·DML·DCL·TCL), 트랜잭션, 테이블 구조를 만드는 **DDL**과 데이터를 다루는 **DML**을 정리했습니다.
테이블·키·관계 개념은 [데이터베이스 기초](데이터베이스기초.md), 조회 문법은 [SQL SELECT](SQL_SELECT.md)를 참고하세요.

> 이 문서의 SQL은 **PostgreSQL** 기준입니다.

## SQL이란

**SQL(Structured Query Language)**은 데이터베이스를 관리하고 데이터를 처리하기 위한 표준 언어다. 삽입·조회·수정·삭제를 수행한다.

- 표준이 있어서 DBMS가 달라도 기본 개념과 주요 명령어 사용법은 공통이다.
- 다만 **데이터 타입, 내장 함수, 자동 증가 값 설정** 같은 세부 문법·동작은 DBMS마다 다를 수 있다.

## 기본 규칙

```sql
SELECT first_name, last_name
FROM employees
WHERE department_id = 100;
```

- 문장은 **세미콜론(`;`)**으로 끝낸다. 여러 줄로 써도 되고, 가독성을 위해 들여쓰기를 권장한다.
- **키워드는 대소문자를 구분하지 않는다.** `SELECT`와 `select`는 같다. 다만 관례상 키워드는 대문자로 쓴다.
- 문법 요소 사이의 공백·줄바꿈은 자유롭다. 아래 세 쿼리는 동일하게 동작한다. (단, 문자열이나 큰따옴표로 감싼 이름 *안*의 공백은 값·이름의 일부라 유지된다.)

```sql
SELECT * FROM employees WHERE salary > 50000;

SELECT *
FROM employees
WHERE salary > 50000;

SELECT    *    FROM   employees
WHERE    salary    >    50000;
```

### 주석

```sql
-- 한 줄 주석

SELECT * FROM employees; -- 문장 뒤에도 쓸 수 있다

/* 여러 줄
   주석은 이렇게 */
```

### 이름과 값 작성

- 테이블명·컬럼명은 `user_profile`처럼 **소문자 + 밑줄(snake_case)**을 권장한다.
- SQL **예약어는 이름으로 쓰지 않는 것**이 좋다. 꼭 써야 하면 큰따옴표(`"`)로 감싼다.
- PostgreSQL은 큰따옴표 없이 쓴 이름을 **소문자로 처리**한다. 큰따옴표로 감싼 이름은 **대소문자를 구분**한다.
- **문자열과 날짜 값은 작은따옴표(`'`)**, 숫자는 따옴표 없이 쓴다.

## SQL 명령어 분류

| 분류 | 이름 | 역할 | 명령어 |
|---|---|---|---|
| **DDL** | Data Definition Language (데이터 정의어) | 데이터베이스 **구조**를 정의·변경 | `CREATE`, `ALTER`, `DROP`, `TRUNCATE` |
| **DML** | Data Manipulation Language (데이터 조작어) | 데이터를 입력·수정·삭제·조회 | `INSERT`, `UPDATE`, `DELETE`, `SELECT` |
| **DCL** | Data Control Language (데이터 제어어) | 접근 **권한** 제어 | `GRANT`, `REVOKE` |
| **TCL** | Transaction Control Language (트랜잭션 제어어) | 트랜잭션 시작, 변경 확정·취소 | `BEGIN`, `COMMIT`, `ROLLBACK` |

- `SELECT`를 **DQL(Data Query Language, 데이터 질의어)**로 따로 분류하기도 한다.

## 트랜잭션

하나 이상의 SQL 작업을 **하나로 묶어 처리하는 논리적 작업 단위**.

- 예: A가 B에게 5만 원을 송금하려면 A 계좌에서 출금하고 B 계좌에 입금해야 한다.
- 출금과 입금을 한 트랜잭션으로 묶으면 두 변경을 **모두 반영하거나 모두 취소**할 수 있다. → "출금만 되고 입금은 안 된" 상태를 막는다.

| 명령 | 동작 |
|---|---|
| `BEGIN` | 트랜잭션 시작 |
| `COMMIT` | 변경을 확정 |
| `ROLLBACK` | 변경을 취소 |

## DDL — 구조 정의

### CREATE

```sql
-- 데이터베이스 생성
CREATE DATABASE demodb;

-- 테이블 생성
CREATE TABLE 테이블명 (
    컬럼명1 데이터타입 [제약조건],
    컬럼명2 데이터타입 [제약조건],
    ...
);
```

#### 주요 데이터 타입

| 분류 | 타입 | 설명 |
|---|---|---|
| 숫자 | `INT` | 정수. 인원수, 수량 등 |
| 숫자 | `BIGINT` | `INT`보다 넓은 범위의 정수 |
| 숫자 | `DECIMAL(전체자리수, 소수자리수)` | **정확한** 십진수. 금액 등 |
| 숫자 | `DOUBLE PRECISION` | 근삿값으로 저장하는 부동소수점. 측정값 등. **오차가 생길 수 있음** |
| 문자 | `CHAR(n)` | 고정 길이. 짧은 값은 남는 길이를 공백으로 채움 |
| 문자 | `VARCHAR(n)` | 최대 n자까지 저장하는 가변 길이 |
| 문자 | `TEXT` | 길이를 미리 정하지 않는 문자열. 본문, 설명 등 |
| 날짜/시간 | `DATE` | 날짜 (`2026-10-01`) |
| 날짜/시간 | `TIME` | 시간 (`14:30:00`) |
| 날짜/시간 | `TIMESTAMP` | 날짜+시간 (`2026-10-01 14:30:00`) |
| 논리 | `BOOLEAN` | `TRUE` / `FALSE`. 활성화 여부 등 |

- PostgreSQL에서 `DECIMAL`과 `NUMERIC`은 같은 타입이다.
- `DECIMAL(10, 2)`는 전체 10자리 중 소수점 아래 2자리 → 정수 부분은 최대 8자리. 소수 2자리를 넘는 값은 **반올림**된다.
- `TIMESTAMP`는 기본적으로 **시간대 정보를 포함하지 않는다.**

#### 제약조건

테이블에 저장할 데이터가 지켜야 하는 규칙. `NULL`은 "값이 없거나 알려지지 않음"을 뜻한다.

| 제약조건 | 설명 | 컬럼 정의 예시 |
|---|---|---|
| `PRIMARY KEY` | 각 행을 구분하는 기본키. 중복·NULL 불가 | `id VARCHAR(7) PRIMARY KEY` |
| `NOT NULL` | NULL 불가 | `name VARCHAR(10) NOT NULL` |
| `UNIQUE` | 값의 중복 불가 | `email VARCHAR(100) UNIQUE` |
| `CHECK` | 저장할 값이 조건을 만족하도록 제한 | `grade INT CHECK (grade BETWEEN 1 AND 4)` |
| `FOREIGN KEY` | 참조 대상 테이블에 있는 키 값만 저장하도록 제한 | `student_id VARCHAR(7) REFERENCES student(id)` |

주의할 점:

- 기본키는 **테이블당 하나**이며, 여러 컬럼을 묶어 하나의 기본키로 지정할 수도 있다.
- PostgreSQL의 `UNIQUE`는 기본적으로 **여러 행의 NULL을 허용**한다.
- `CHECK`와 외래키만으로는 **NULL을 막지 못한다.** 값을 반드시 받으려면 `NOT NULL`을 함께 지정한다.

#### 외래키(FOREIGN KEY)와 참조 무결성

참조 대상 테이블의 키와 연결해 **존재하지 않는 대상을 가리키는 데이터가 저장되지 않도록** 하는 제약조건. 이것을 **참조 무결성**이라고 한다. 참조 대상은 보통 `PRIMARY KEY`나 `UNIQUE`가 지정된 컬럼이다.

컬럼 정의에 `REFERENCES`를 붙이는 방식:

```sql
student_id VARCHAR(7) REFERENCES student(id)
```

테이블 수준에서 따로 지정하는 방식 (같은 의미):

```sql
student_id VARCHAR(7),
FOREIGN KEY (student_id) REFERENCES student(id)
```

동작 규칙 (`student`가 참조 대상, `attendance`가 참조하는 테이블일 때):

- `student.id`에 `'2024001'`이 있어야 그 학번의 출결을 저장할 수 있다. 없는 학번을 입력하거나 그 값으로 바꾸면 **오류**가 난다.
- 한 학생의 여러 출결 기록이 같은 학번을 참조할 수 있다. **외래키는 값의 중복을 막지 않는다.**
- `NOT NULL`을 지정하지 않으면 `student_id`에 NULL도 저장할 수 있다.
- 별도 옵션이 없으면, 출결 기록이 참조 중인 학생을 **삭제하거나 학번을 변경하면 오류**가 난다. 기존 기록이 가리킬 학생이 사라지는 것을 막기 위해서다.

#### 기본값과 자동 생성 값

- `DEFAULT`는 제약조건이 아니라 **값을 생략했을 때 쓸 기본값**이다. 예: `grade INT DEFAULT 1`
  - 값을 명시적으로 `NULL`로 넣으면 기본값으로 바뀌지 **않는다.**
- `GENERATED ALWAYS AS IDENTITY`는 정수 컬럼 값을 **자동 생성**한다. 예: `attendance_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`
  - 자동 생성만으로 중복이 막히는 건 아니므로, 기본키로 쓸 땐 `PRIMARY KEY`를 함께 지정한다.

#### 테이블 생성 예제

```sql
-- 기본적인 테이블
CREATE TABLE student (
    id VARCHAR(7) PRIMARY KEY,
    name VARCHAR(10),
    grade INT,
    major VARCHAR(20)
);

-- 외래키가 있는 테이블
CREATE TABLE attendance (
    attendance_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id VARCHAR(7) REFERENCES student(id),
    date DATE,
    status VARCHAR(10)
);
```

### ALTER — 테이블 변경

```sql
-- 컬럼 추가
ALTER TABLE student
ADD phone VARCHAR(20);

-- 컬럼 이름 수정
ALTER TABLE student
RENAME COLUMN phone TO phone_number;

-- 컬럼 타입 변경
ALTER TABLE student
ALTER COLUMN name TYPE VARCHAR(100);

-- 컬럼 삭제
ALTER TABLE student
DROP COLUMN phone_number;
```

### DROP / TRUNCATE — 삭제

```sql
DROP DATABASE demodb;      -- 데이터베이스 삭제
DROP TABLE attendance;     -- 테이블 삭제 (구조째 삭제)
TRUNCATE TABLE student;    -- 테이블 구조는 두고 데이터 전체 삭제
```

## DML — 데이터 조작

### INSERT — 추가

모든 컬럼의 값을 순서대로 다 적으면 컬럼 목록은 생략할 수 있다.

```sql
INSERT INTO 테이블명 (컬럼1, 컬럼2) VALUES (값1, 값2);

INSERT INTO student (id, name, grade, major)
VALUES ('2024001', '김철수', 1, '컴퓨터공학');

-- 여러 행을 한 번에, 컬럼 목록 생략
INSERT INTO student VALUES
    ('2024002', '이영희', 2, '경영학'),
    ('2024003', '박민수', 3, '물리학');
```

### SELECT — 조회

```sql
SELECT * FROM student;                      -- 모든 필드
SELECT id, name FROM student;               -- 특정 필드
SELECT * FROM student WHERE grade = 2;      -- 조건 필터링
```

- 컬럼명 앞에 `테이블명.`을 붙여 소속을 밝힐 수 있다. 여러 테이블에 같은 이름의 컬럼이 있을 때 구분하며, 모호하지 않으면 생략한다.
- 자세한 문법은 [SQL SELECT](SQL_SELECT.md).

### UPDATE — 수정

```sql
UPDATE 테이블명 SET 컬럼 = 새값 WHERE 조건;

UPDATE student
SET grade = 2, major = '경제학'
WHERE id = '2024001';
```

### DELETE — 삭제

```sql
DELETE FROM 테이블명 WHERE 조건;

DELETE FROM student
WHERE id = '2024002';
```

> ⚠️ **`UPDATE`와 `DELETE`에서 `WHERE`를 생략하면 모든 행이 수정·삭제된다.** 특정 행만 처리하려면 반드시 조건을 지정한다.

## DELETE vs TRUNCATE vs DROP

| | 대상 | 조건 지정 | 결과 |
|---|---|---|---|
| `DELETE` | 행 (DML) | `WHERE`로 가능 | 조건에 맞는 행만 삭제 |
| `TRUNCATE` | 테이블의 모든 행 (DDL) | 불가 | 구조는 남기고 데이터 전체 삭제 |
| `DROP` | 테이블·DB 자체 (DDL) | 불가 | 구조까지 통째로 삭제 |

## 정리

- SQL은 표준이지만 타입·함수·자동 증가 등 세부는 DBMS마다 다르다. 이 문서는 PostgreSQL 기준.
- 명령어는 DDL(구조) / DML(데이터) / DCL(권한) / TCL(트랜잭션)으로 나뉜다.
- 트랜잭션은 여러 작업을 모두 반영하거나 모두 취소하게 묶는다.
- 제약조건과 외래키(참조 무결성)로 잘못된 데이터가 들어오는 것을 DB가 막게 한다.
- `UPDATE`/`DELETE`는 `WHERE`를 빼먹지 않는다.
