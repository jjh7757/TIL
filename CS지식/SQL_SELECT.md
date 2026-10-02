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

## 실습 문제

수업에서 받은 문제입니다. 풀이는 직접 풀어 보며 채워 나갈 예정이라 문제만 적어 둡니다.

<details>
<summary>WHERE (10문제)</summary>

1. 인구가 800만 이상인 도시의 `name`, `population`
2. 한국(KOR)에 있는 도시의 `name`, `code`
3. 유럽 대륙 나라들의 `name`, `region`
4. 이름이 'San'으로 시작하는 도시의 `name`
5. 독립 연도(`indepyear`)가 1901년 이상인 나라의 `name`, `indepyear`
6. 인구가 100만~200만 사이인 한국 도시의 `name`
7. 인구가 500만 이상인 한국·일본·중국 도시의 `name`, `code`, `population`
8. 도시 이름이 'A'로 시작하고 'a'로 끝나는 도시의 `name`
9. 동남아시아(Southeast Asia) 지역에 속하지 않는 아시아 대륙 나라들의 `name`, `region`
10. 오세아니아 대륙에서 기대수명 데이터가 없는 나라의 `name`, `lifeexpectancy`, `continent`

</details>

<details>
<summary>ORDER BY / LIMIT·OFFSET (5문제)</summary>

1. `country`를 대륙별로 정렬하고, 같은 대륙 안에서는 GNP 높은 순으로 `name`, `continent`, `gnp`
2. 기대수명이 높은 순으로 정렬하되 NULL은 마지막에 오도록 `name`, `lifeexpectancy`
3. `city`에서 인구수가 가장 적은 도시 5개
4. `country`에서 면적(`surfacearea`)이 넓은 순으로 11~20위 국가
5. `country`에서 기대수명이 높은 순으로 1~5위 국가

</details>

<details>
<summary>GROUP BY (7문제)</summary>

1. 대륙별 총 인구수
2. 대륙별 평균 GNP와 평균 인구
3. 인구 50만 이상 100만 이하 도시를 대상으로, `countrycode`와 `district`별 도시 수
4. 아시아 대륙 국가들의 Region별 총 GNP
5. 대륙별 국가 수가 많은 순서대로 `continent`, 국가 수
6. 독립년도가 있는 국가들의 대륙별 평균 기대수명이 높은 순서대로 `continent`, 평균 기대수명
7. Region별 총 GNP를 구하고, 총 GNP가 가장 높은 Region

</details>

<details>
<summary>HAVING (6문제)</summary>

1. 국가별 도시가 10개 이상인 국가의 `countrycode`, 도시 수
2. `countrycode`·`district`별로 집계해 평균 인구 100만 이상이면서 도시 수 3개 이상인 그룹의 `countrycode`, `district`, 도시 수, 총 인구
3. 아시아 대륙 국가들 중 Region별 평균 GNP가 1000 이상인 Region, 평균 GNP
4. 독립년도가 1900년 이후인 국가들 중 대륙별 평균 기대수명이 70세 이상인 `continent`, 평균 기대수명
5. 도시 평균 인구가 100만 이상이고 도시 최소 인구가 50만 이상인 국가의 `countrycode`, 총 도시 수, 총 인구수
6. 인구 50만 이상인 도시만 대상으로 국가별 집계해, 평균 인구가 100만 이상인 국가의 `countrycode`, 해당 도시 수, 인구 합계

</details>

## 정리

- `SELECT`는 **FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT** 순서로 실행된다. 쓰는 순서와 다르다.
- `NULL`은 `= NULL`이 아니라 `IS NULL`로 확인하고, 집계 함수(`COUNT(*)` 제외)는 NULL을 무시한다.
- `AND`는 `OR`보다 먼저 계산되므로 섞어 쓸 땐 괄호로 묶는다.
- 페이징은 `ORDER BY` + `LIMIT` + `OFFSET`, `OFFSET`은 (페이지 − 1) × 개수.
- 행을 거르려면 `WHERE`, 집계된 그룹을 거르려면 `HAVING`. 별칭은 `HAVING`에서 못 쓴다.
