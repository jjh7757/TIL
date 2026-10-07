# SQL 서브쿼리(Subquery)

다른 SQL 문 안에 포함된 조회 쿼리인 서브쿼리를 **어느 절에 넣느냐**(`WHERE`·`SELECT`·`IN`·`FROM`)와 바깥 쿼리를 참조하는 상관 서브쿼리 중심으로 정리했습니다.
`JOIN`은 [SQL JOIN](SQL_JOIN.md), `HAVING`과 집계는 [SQL SELECT](SQL_SELECT.md)를 참고하세요.

> PostgreSQL 기준. 예제 DB는 `world`(`city`, `country`)입니다.

## 서브쿼리란

- 괄호 `()` 안에 작성한 조회 쿼리이며, 그 결과를 바깥 쿼리에서 사용한다.
- 이 문서의 예제 외에도 `EXISTS`로 조건에 맞는 행의 존재 여부를 확인하거나 `HAVING`에서 그룹을 필터링하는 데도 쓸 수 있다.

| 위치 | 서브쿼리 결과의 모양 | 용도 |
|------|----------------------|------|
| `WHERE` (`>`, `=` 등) | 한 컬럼, 최대 한 행 | 하나의 값을 조건으로 |
| `SELECT` | 한 컬럼, 최대 한 행 | 출력할 값으로 |
| `WHERE ... IN` | 한 컬럼, 여러 행 | 값 목록을 조건으로 |
| `FROM` | 여러 컬럼, 여러 행 | 하나의 테이블처럼 |

## WHERE 절 — 하나의 값을 조건으로

전체 도시의 평균 인구보다 인구가 많은 도시를 조회한다. 내부 쿼리는 평균을 **하나의 값**으로 반환한다.

```sql
SELECT AVG(population) FROM city;       -- 먼저 이 쿼리의 결과를
```

```sql
SELECT name, population
FROM city
WHERE population > (
    SELECT AVG(population)
    FROM city
);                                       -- WHERE에 넣어 비교
```

- 괄호 안의 쿼리를 **하나의 평균값으로 바꿔 읽으면** 된다.
- 평균을 직접 계산해 입력하지 않아도 되므로 데이터가 바뀌어도 쿼리를 고칠 필요가 없다.

## SELECT 절 — 출력할 값으로

각 도시의 이름·인구 옆에 전체 평균 인구를 함께 표시한다.

```sql
SELECT name,
       population,
       (SELECT AVG(population) FROM city) AS avg_population
FROM city;
```

- `avg_population`은 출력 컬럼의 별칭이고, **모든 행에 같은 평균**이 표시된다.

> **단일 값 서브쿼리의 규칙**: 위 두 예제처럼 서브쿼리 결과를 하나의 값으로 쓸 때는 **한 컬럼, 최대 한 행**이어야 한다. 결과가 없으면 `NULL`, 여러 행을 반환하면 오류가 난다.

## IN — 여러 행의 결과를 조건으로

인구가 500만 이상인 도시가 있는 국가의 코드와 이름을 조회한다. 내부 쿼리는 국가 코드를 한 컬럼의 **여러 행**으로 반환한다.

```sql
SELECT countrycode
FROM city
WHERE population >= 5000000;
```

```sql
SELECT code, name
FROM country
WHERE code IN (
    SELECT countrycode
    FROM city
    WHERE population >= 5000000
);
```

- 바깥 쿼리는 국가 코드가 서브쿼리 결과에 **포함되는** 국가를 조회한다.
- 서브쿼리 결과에 같은 국가 코드가 여러 번 나와도 바깥 쿼리의 국가가 중복 출력되지는 않는다. `IN`은 포함 여부만 확인하기 때문이다. (`JOIN`이었다면 도시 수만큼 행이 반복된다.)

## FROM 절 — 하나의 테이블처럼

인구가 가장 많은 도시 5개의 평균 인구를 구한다.

```sql
SELECT AVG(population) AS avg_population
FROM (
    SELECT name, population
    FROM city
    ORDER BY population DESC, id
    LIMIT 5
) AS top_cities;
```

- 서브쿼리 결과가 `name`, `population` 컬럼을 가진 **테이블처럼** 쓰이고, `top_cities`는 그 별칭이다. PostgreSQL에서 `FROM`의 서브쿼리에는 별칭이 필요하다.
- `ORDER BY population DESC, id`: 인구가 같으면 `id`가 작은 도시를 먼저 골라 **결과가 항상 같게** 한다.
- `SELECT AVG(population) FROM city LIMIT 5`는 전체 평균을 구한 **한 행에** `LIMIT`을 적용할 뿐이다. 상위 5개의 평균은 서브쿼리에서 5개를 먼저 고른 뒤 바깥에서 평균을 내야 한다.

## 상관 서브쿼리 — 바깥 쿼리의 값을 참조

지금까지의 서브쿼리는 단독으로 실행할 수 있었다. **상관 서브쿼리**는 바깥 쿼리의 값을 참조하므로 단독으로 실행할 수 없다.

각 국가에서 인구가 가장 많은 도시를 조회한다.

```sql
SELECT c.name, c.countrycode, c.population
FROM city AS c
WHERE c.population = (
    SELECT MAX(c2.population)
    FROM city AS c2
    WHERE c2.countrycode = c.countrycode
);
```

- `c`는 바깥 쿼리의 도시, `c2`는 서브쿼리의 도시를 구분하는 별칭이다. (같은 테이블이라 [Self JOIN](SQL_JOIN.md)처럼 별칭이 필수)
- 서브쿼리가 바깥의 `c.countrycode`를 참조해 **같은 국가 도시들의 최대 인구**를 구한다.
- 즉 "각 도시를 자기 국가의 최대 인구와 비교"하는 쿼리다. 최대 인구가 같은 도시가 여럿이면 **모두** 조회된다.

## 장단점

**장점**
- 복잡한 조회를 내부 쿼리와 바깥 쿼리로 나눠 표현할 수 있다.
- 조회 결과를 조건에 바로 쓸 수 있어 값을 따로 구해 입력할 필요가 없다.
- 조회 결과를 하나의 테이블처럼 추가 가공할 수 있다.

**단점·주의점**
- 중첩이 깊어지면 흐름을 이해하고 수정하기 어렵다.
- 상관 서브쿼리에서 반복 조회가 일어나면 데이터가 많을수록 처리 비용이 커질 수 있다.
- 서브쿼리가 항상 `JOIN`보다 느린 것은 아니다. 성능은 쿼리 구조, [인덱스](SQL_인덱스.md), DB의 실행 계획에 따라 달라진다.

## 정리

- 서브쿼리는 **들어가는 위치에 따라 결과의 모양(값 하나 / 값 목록 / 테이블)이 달라진다.**
- 비교 연산자(`>`, `=`)에는 한 행 이하, `IN`에는 한 컬럼 여러 행, `FROM`에는 테이블 형태.
- 바깥 쿼리의 컬럼을 참조하면 상관 서브쿼리 — 행마다 서브쿼리가 다시 평가되는 것으로 이해한다.
