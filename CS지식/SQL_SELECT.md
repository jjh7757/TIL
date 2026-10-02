# SQL SELECT

데이터를 조회하는 `SELECT`의 전체 구조를 기본(`WHERE`·정렬·페이징)과 심화(`GROUP BY`·집계·`HAVING`)로 나눠 정리했습니다.
테이블 생성과 `INSERT`/`UPDATE`/`DELETE`는 [SQL 기초: DDL과 DML](SQL기초_DDL_DML.md)를 참고하세요.

> PostgreSQL 기준. 예제는 `country`(국가), `city`(도시) 테이블을 사용합니다.

## SELECT의 전체 구조

```sql
SELECT [DISTINCT] column1 [, column2 ...]
FROM table_name [AS alias]
[WHERE condition]
[GROUP BY column1]
[HAVING group_condition]
[ORDER BY column1 [ASC | DESC]]
[LIMIT N] [OFFSET M];
```

- `[]`는 생략 가능, `|`는 선택, `...`은 같은 형식을 더 나열할 수 있다는 뜻이다. 실제 SQL에는 입력하지 않는다.

### 논리적 처리 순서

쓰는 순서와 **실행되는 순서가 다르다.**

```
FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT
```

`WHERE`로 행을 거른 뒤 `GROUP BY`로 묶어 집계하고, 그 결과를 `HAVING`으로 거른다. 그래서 `SELECT`에서 붙인 별칭은 `HAVING`에서 쓸 수 없다. (아래 참고)

## 기본 SELECT

### 컬럼 선택

```sql
SELECT * FROM country;                          -- 모든 필드
SELECT name, continent FROM country;            -- 특정 필드
SELECT country.name, country.continent FROM country;   -- 테이블명으로 소속 명시
```

- 컬럼명에 띄어쓰기가 있으면 `""`로 감싸 하나의 이름으로 인식시킨다.
- 컬럼 앞의 `테이블명.`은 같은 이름의 컬럼이 여러 테이블에 있을 때 모호함을 막는다. 단일 테이블 조회에서는 생략할 수 있다.

### 별칭(alias)

```sql
-- 테이블 별칭 (AS 생략 가능)
SELECT t.컬럼명1, t.컬럼명2 FROM 테이블명 AS t;
SELECT t.컬럼명1, t.컬럼명2 FROM 테이블명 t;

-- 컬럼 별칭: 조회 결과에 표시되는 이름만 바뀌고 원본 컬럼명은 그대로
SELECT c.name AS 국가, c.population AS 인구 FROM country c;
SELECT c.name 국가, c.population 인구 FROM country c;
```

### DISTINCT — 중복 제거

```sql
SELECT DISTINCT continent FROM country;              -- 대륙의 종류

SELECT DISTINCT continent, region FROM country;      -- (대륙, 지역) 조합별로 중복 제거
```

여러 컬럼을 지정하면 **컬럼 값의 조합이 같은 행**의 중복을 제거한다. 대륙 이름은 반복돼도 같은 (대륙, 지역) 조합은 한 번만 나온다.

## WHERE — 조건 필터링

문자는 작은따옴표 `''`를 쓴다.

### 비교 연산자

```sql
WHERE population > 1000000
WHERE population >= 1000000
WHERE population < 1000000
WHERE population <= 1000000
WHERE population = 1000000
WHERE population != 1000000   -- 또는 <>
```

### 논리 연산자

```sql
WHERE population > 1000000 AND continent = 'Asia'
WHERE population > 1000000 OR continent = 'Asia'
WHERE NOT population < 1000000
```

**`AND`가 `OR`보다 먼저 계산된다.** 먼저 계산할 조건은 괄호로 묶는다.

```sql
-- 인구 100만 초과이면서 아시아 또는 유럽
SELECT name, continent, population
FROM country
WHERE population > 1000000
  AND (continent = 'Asia' OR continent = 'Europe');
```

### 범위, 포함

```sql
WHERE population BETWEEN 1000000 AND 2000000       -- 시작값·끝값 모두 포함
WHERE population NOT BETWEEN 1000000 AND 2000000

WHERE code IN ('KOR', 'JPN', 'CHN')
WHERE code NOT IN ('KOR', 'JPN', 'CHN')
```

### NULL 확인

`NULL`은 "값이 없거나 알려지지 않음"이다. **`= NULL`, `!= NULL`로 비교하지 않고** `IS NULL`, `IS NOT NULL`을 쓴다.

```sql
WHERE lifeexpectancy IS NULL
WHERE lifeexpectancy IS NOT NULL
```

### 패턴 매칭 — LIKE

| 기호 | 의미 |
|---|---|
| `%` | 0개 이상의 문자 |
| `_` | 정확히 1개의 문자 |

```sql
WHERE name LIKE 'S%'        -- S로 시작
WHERE name LIKE '%on'       -- on으로 끝남
WHERE name LIKE '%on%'      -- on이 포함
WHERE name NOT LIKE 'S%'    -- S로 시작하지 않음
```

`LIKE` 대신 `ILIKE`를 쓰면 **대소문자를 구분하지 않는다.**

## ORDER BY — 정렬

```sql
ORDER BY 컬럼명 [ASC | DESC]
```

- `ASC` 오름차순(기본값, 생략 가능), `DESC` 내림차순.
- 여러 컬럼을 쓰면 **앞 컬럼으로 먼저 정렬하고, 같은 값끼리 다음 컬럼으로** 정렬한다.

```sql
-- 인구 많은 순
SELECT name, population FROM city ORDER BY population DESC;

-- 국가순, 같은 국가 안에서는 인구 많은 순
SELECT name, code, population FROM city ORDER BY code, population DESC;
```

### NULL의 위치

PostgreSQL은 기본적으로 `ASC`에서 NULL이 **마지막**, `DESC`에서 **처음**에 온다. `NULLS FIRST` / `NULLS LAST`로 지정할 수 있다.

```sql
SELECT name, indepyear FROM country ORDER BY indepyear DESC;              -- NULL이 맨 위
SELECT name, indepyear FROM country ORDER BY indepyear DESC NULLS LAST;   -- NULL을 아래로
SELECT name, indepyear FROM country ORDER BY indepyear ASC NULLS FIRST;   -- NULL을 위로
```

## LIMIT, OFFSET — 일부만 조회

- `LIMIT`: 반환할 행 수 (= 한 페이지에 보여줄 개수)
- `OFFSET`: 앞에서 건너뛸 행 수 = **(페이지 번호 − 1) × 페이지당 개수**
- 원하는 순서의 일부를 얻으려면 **`ORDER BY`와 함께** 쓴다.

```sql
-- 인구 상위 1~5위 (1페이지)
SELECT name, population FROM city ORDER BY population DESC LIMIT 5;   -- OFFSET 0 생략

-- 인구 상위 11~15위 (3페이지)
SELECT name, population FROM city ORDER BY population DESC LIMIT 5 OFFSET 10;
```

## GROUP BY — 그룹화와 집계

지정한 컬럼 기준으로 행을 그룹화하고, 그룹마다 **집계 함수**를 적용한다.
그룹별 결과에는 `GROUP BY`에 지정한 컬럼, 집계 함수, 그리고 이들로 만든 계산식을 쓸 수 있다.

### 집계 함수

여러 행을 요약해 **하나의 값**을 돌려주는 함수.

| 함수 | 의미 |
|---|---|
| `COUNT(*)` | 전체 행 개수 |
| `COUNT(컬럼)` | 해당 컬럼이 **NULL이 아닌** 행 개수 |
| `SUM(컬럼)` | 합계 |
| `AVG(컬럼)` | 평균 |
| `MIN(컬럼)` / `MAX(컬럼)` | 최솟값 / 최댓값 |

`SUM`, `AVG`, `MIN`, `MAX`는 **NULL을 제외하고** 계산한다.

```sql
-- 대륙별 국가 수
SELECT continent, COUNT(*) AS country_count
FROM country
GROUP BY continent;

-- Region별 평균 인구
SELECT region, AVG(population) AS avg_pop
FROM country
GROUP BY region;

-- 대륙별 최소/최대 인구
SELECT continent,
       MIN(population) AS min_pop,
       MAX(population) AS max_pop
FROM country
GROUP BY continent;

-- 아시아 국가들의 Region별 국가 수 (WHERE로 먼저 거르고 그룹화)
SELECT region, COUNT(*) AS country_count
FROM country
WHERE continent = 'Asia'
GROUP BY region;

-- 여러 컬럼: 값의 조합별로 그룹화
SELECT continent, governmentform, COUNT(*)
FROM country
GROUP BY continent, governmentform
ORDER BY continent, governmentform;
```

## HAVING — 그룹 결과에 조건 걸기

| | 걸러내는 대상 | 실행 시점 |
|---|---|---|
| `WHERE` | **개별 행** | 그룹화 *전* |
| `HAVING` | **그룹화·집계된 결과** | 그룹화 *후* (집계 함수와 함께 쓰는 경우가 많음) |

```sql
-- 국가 수가 20개가 넘는 대륙
SELECT continent, COUNT(*) AS country_count
FROM country
GROUP BY continent
HAVING COUNT(*) > 20;
```

- **`SELECT`의 별칭은 `HAVING`에서 쓸 수 없다.** (`HAVING`이 `SELECT`보다 먼저 실행되므로) 집계 함수를 그대로 다시 쓴다.
- `HAVING`에는 `SELECT`에 없는 집계 함수도 쓸 수 있다.

```sql
-- Region별 평균 인구가 1000만 초과
SELECT region, AVG(population) AS avg_pop
FROM country
GROUP BY region
HAVING AVG(population) > 10000000;

-- WHERE + GROUP BY + HAVING 함께: 인구 1000만 이상 국가가 10개 넘는 대륙
SELECT continent, COUNT(*) AS big_countries
FROM country
WHERE population >= 10000000
GROUP BY continent
HAVING COUNT(*) > 10;

-- SELECT에 없는 집계로 거르기: 평균 인구가 1000만 초과인 대륙의 국가 수
SELECT continent, COUNT(*) AS country_count
FROM country
GROUP BY continent
HAVING AVG(population) > 10000000;
```

`WHERE`에서 거르는 것과 `HAVING`에서 거르는 것은 의미가 다르다. "인구 1000만 이상인 *국가*만 세기"는 `WHERE`, "국가 수가 10개 넘는 *대륙*만 남기기"는 `HAVING`.

## 정리

- `SELECT`는 **FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT** 순서로 실행된다. 쓰는 순서와 다르다.
- `NULL`은 `= NULL`이 아니라 `IS NULL`로 확인하고, 집계 함수(`COUNT(*)` 제외)는 NULL을 무시한다.
- `AND`는 `OR`보다 먼저 계산되므로 섞어 쓸 땐 괄호로 묶는다.
- 페이징은 `ORDER BY` + `LIMIT` + `OFFSET`, `OFFSET`은 (페이지 − 1) × 개수.
- 행을 거르려면 `WHERE`, 집계된 그룹을 거르려면 `HAVING`. 별칭은 `HAVING`에서 못 쓴다.
