# SQL JOIN

두 개 이상의 테이블을 연결해 조회하는 `JOIN`의 종류와 차이, `ON`과 `WHERE`의 차이, 여러 테이블을 잇는 실전 예제를 정리했습니다.
`SELECT`의 기본 구조와 `GROUP BY`·`HAVING`은 [SQL SELECT](SQL_SELECT.md), 테이블 관계(1:N·M:N)는 [데이터베이스 기초](데이터베이스기초.md)를 참고하세요.

> PostgreSQL 기준. 예제 DB는 `world`(`country`, `city`, `countrylanguage`)와 `dvdrental`(`film`, `actor`, `customer` 등)입니다.

## 기본 구조

```sql
SELECT 컬럼명
FROM 테이블1
JOIN유형 테이블2 ON 조인조건;
```

- `ON`에 두 테이블의 행을 연결하는 조건(보통 PK = FK)을 쓴다.
- `JOIN` 뒤에 테이블을 계속 이어 붙이면 3개 이상도 연결할 수 있다.

## JOIN의 종류

| 종류 | 결과 |
|------|------|
| `INNER JOIN` | 조인 조건이 **일치하는 행만** |
| `LEFT JOIN` | **왼쪽 테이블 전부** + 오른쪽의 일치하는 행 (없으면 NULL) |
| `RIGHT JOIN` | **오른쪽 테이블 전부** + 왼쪽의 일치하는 행 (없으면 NULL) |
| `FULL JOIN` | 양쪽 모두 유지, 일치하지 않는 쪽은 NULL |

### INNER JOIN

- 두 테이블에서 조건이 일치하는 레코드만 반환한다.
- `INNER`를 생략하고 `JOIN`만 써도 `INNER JOIN`으로 동작한다.

**도시와 국가 연결 (`world`, 1:N)**

```sql
SELECT city.name AS cityname,
       country.name AS countryname,
       country.continent
FROM city
INNER JOIN country ON city.countrycode = country.code;

-- INNER 생략
SELECT city.name AS cityname,
       country.name AS countryname,
       country.continent
FROM city
JOIN country ON city.countrycode = country.code;
```

**배우와 출연 영화 (`dvdrental`, M:N)**

M:N 관계는 연관 테이블(`film_actor`)을 사이에 두고 `JOIN`을 두 번 한다. 두 개의 1:N으로 나눠 이어 붙이는 셈이다.

```sql
SELECT actor.first_name,
       actor.last_name,
       film.title
FROM actor
INNER JOIN film_actor ON actor.actor_id = film_actor.actor_id
INNER JOIN film ON film_actor.film_id = film.film_id;
```

### LEFT JOIN

왼쪽 테이블의 행은 짝이 없어도 **모두 유지**한다. 짝이 없는 행의 오른쪽 컬럼은 NULL이 된다.

**모든 국가와 수도 (`world`, 1:1)**

```sql
SELECT country.name AS country_name,
       city.name AS capital_city
FROM country
LEFT JOIN city ON country.capital = city.id;
```

수도 정보가 없는 국가만 보려면 오른쪽 PK가 NULL인 행을 찾는다.

```sql
SELECT country.name AS country_name,
       city.name AS capital_city
FROM country
LEFT JOIN city ON country.capital = city.id
WHERE city.id IS NULL;
```

같은 데이터를 `INNER JOIN`으로 조회하면 수도에 해당하는 도시 데이터가 없는 국가는 **결과에서 사라진다.**

```sql
SELECT country.name AS country_name,
       city.name AS capital_city
FROM country
INNER JOIN city ON country.capital = city.id
WHERE country.name = 'Antarctica';   -- 결과 0행
```

**모든 영화의 재고 (`dvdrental`, 1:N)**

영화 하나에 재고가 여러 개면 **재고마다 영화 정보가 반복**해서 나온다.

```sql
SELECT f.film_id, f.title, i.inventory_id
FROM film f
LEFT JOIN inventory i ON f.film_id = i.film_id;

-- 재고가 하나도 없는 영화
SELECT f.film_id, f.title, i.inventory_id
FROM film f
LEFT JOIN inventory i ON f.film_id = i.film_id
WHERE i.inventory_id IS NULL;
```

**모든 영화와 대여 고객 (`dvdrental`, M:N)**

`LEFT JOIN`을 연달아 쓰면 앞 단계에서 NULL이 된 행도 끝까지 유지된다.

```sql
SELECT f.title,
       c.customer_id,
       c.first_name,
       c.last_name,
       r.rental_date
FROM film f
LEFT JOIN inventory i ON f.film_id = i.film_id
LEFT JOIN rental r ON i.inventory_id = r.inventory_id
LEFT JOIN customer c ON r.customer_id = c.customer_id;
```

- 같은 고객이 같은 영화를 여러 번 빌렸다면 **대여 기록마다** 행이 나온다.
- 재고가 없거나 재고의 대여 기록이 없으면 고객 정보와 대여일은 NULL이다.

### FROM에 어떤 테이블을 둘까

- `INNER JOIN`: 조회의 **기준이 되는 테이블**을 `FROM`에 두면 읽기 쉽다.
- `LEFT JOIN`: 연결되는 데이터가 없어도 **모든 행을 유지하고 싶은 테이블**을 `FROM`에 둔다.

### RIGHT JOIN

오른쪽 테이블의 모든 행을 유지한다. `LEFT JOIN`에서 테이블 순서만 바꾸면 같은 결과라 실무에서는 잘 쓰지 않는다.

### FULL JOIN

조건이 일치하는 행을 연결하고, 양쪽의 일치하지 않는 행도 모두 포함한다. 짝이 없는 쪽의 컬럼은 NULL이다.

### Self JOIN

JOIN의 한 종류가 아니라 **같은 테이블을 자기 자신과 조인하는 방식**이다. `INNER`, `LEFT` 등 어느 유형과도 함께 쓸 수 있다.

- 조직도·댓글처럼 **계층 구조**를 표현할 때
- 같은 테이블 안에서 **행끼리 비교**해야 할 때
- 순위나 그룹 내 비교가 필요할 때

같은 테이블이 두 번 나오므로 **별칭으로 구분하는 것이 필수**다.

**같은 영화에 출연한 배우 쌍 (`dvdrental`)**

```sql
SELECT a.actor_id AS actor_1,
       b.actor_id AS actor_2,
       a.film_id
FROM film_actor a
JOIN film_actor b ON a.film_id = b.film_id
WHERE a.actor_id < b.actor_id;
```

- `a`와 `b`는 같은 `film_actor` 테이블을 구분하기 위한 별칭이다.
- `a.actor_id < b.actor_id`는 자기 자신과의 조합과, 순서만 바뀐 중복 조합을 제외한다. `(1, 2)`는 남기고 `(1, 1)`과 `(2, 1)`은 제외한다.

**댓글 - 대댓글 관계**

`parent_id`가 같은 테이블의 `id`를 가리키는 구조다. 원댓글은 `parent_id`가 NULL이다.

```sql
CREATE TABLE comments (
    id INT PRIMARY KEY,
    content TEXT,
    parent_id INT,
    FOREIGN KEY (parent_id) REFERENCES comments(id)
);

INSERT INTO comments VALUES
(1, '안녕하세요', NULL),           -- 원댓글
(2, '반갑습니다', NULL),           -- 원댓글
(3, '네 안녕하세요!', 1),          -- 1번 댓글의 대댓글
(4, '저도 반가워요', 1),           -- 1번 댓글의 대댓글
(5, '답글 드립니다', 2),           -- 2번 댓글의 대댓글
(6, '안녕', NULL);                -- 원댓글
```

```sql
-- 모든 댓글
SELECT c.id AS comment_id, c.content AS comment_content
FROM comments c;

-- 원댓글만
SELECT parent.id AS parent_id, parent.content AS parent_content
FROM comments parent
WHERE parent.parent_id IS NULL;

-- 원댓글과 대댓글을 함께
SELECT parent.id AS parent_id,
       parent.content AS parent_content,
       child.id AS reply_id,
       child.content AS reply_content
FROM comments parent
LEFT JOIN comments child ON child.parent_id = parent.id
WHERE parent.parent_id IS NULL;   -- 원댓글만 기준으로
```

- 원댓글과 **바로 아래 대댓글까지만** 조회한다. 대댓글에 달린 답글은 포함하지 않는다.
- `LEFT JOIN`이라 대댓글이 없는 원댓글도 나온다. 예제의 6번은 `reply_id`, `reply_content`가 NULL이다.
- 여기서 `WHERE parent.parent_id IS NULL`은 **왼쪽(parent) 테이블 조건**이라 LEFT JOIN의 "왼쪽 유지"를 깨지 않는다. (오른쪽 조건을 `WHERE`에 쓰면 안 되는 경우와 구분할 것)

## ON과 WHERE의 차이

- `ON`: 두 테이블의 행을 **연결하는** 조건
- `WHERE`: 조인 결과에서 **남길 행을 고르는** 조건

`INNER JOIN`에서는 어디에 써도 결과가 같지만, **`LEFT JOIN`에서는 오른쪽 테이블 조건을 어디에 쓰느냐에 따라 결과가 달라진다.**

**`ON`에 쓰면 — 모든 영화를 유지하고, 1번 매장의 재고만 연결**

```sql
SELECT f.film_id, f.title, i.inventory_id, i.store_id
FROM film f
LEFT JOIN inventory i ON f.film_id = i.film_id
                     AND i.store_id = 1;
```

1번 매장에 재고가 없는 영화도 조회되고, 그 영화의 재고 컬럼은 NULL이다.

**`WHERE`에 쓰면 — 1번 매장에 재고가 있는 영화만**

```sql
SELECT f.film_id, f.title, i.inventory_id, i.store_id
FROM film f
LEFT JOIN inventory i ON f.film_id = i.film_id
WHERE i.store_id = 1;
```

`WHERE`는 조인이 끝난 뒤 적용된다. 재고가 NULL인 행은 `NULL = 1`이 참이 아니라서 걸러지므로, 사실상 `INNER JOIN`과 같은 결과가 된다.

> 오른쪽 테이블에 조건을 걸면서 `LEFT JOIN`의 "왼쪽 전부 유지"를 지키고 싶다면 조건을 `ON`에 둔다.

## 예제: world

**어느 나라에 속한 도시인지**

```sql
SELECT co.name AS country_name,
       ci.name AS city_name
FROM city ci
JOIN country co ON ci.countrycode = co.code;
```

**국가와 그 국가의 공식 수도 매칭** — `country.capital`이 `city.id`를 가리킨다.

```sql
SELECT co.name AS country_name,
       ci.name AS capital_city
FROM country co
JOIN city ci ON co.capital = ci.id;
```

**특정 대륙의 도시 목록**

```sql
SELECT co.continent,
       co.name AS country_name,
       ci.name AS city_name
FROM country co
JOIN city ci ON co.code = ci.countrycode
WHERE co.continent = 'Asia'
ORDER BY co.name, ci.name;
```

**아시아에서 인구 500만 명 이상인 도시**

```sql
SELECT co.continent,
       co.name AS country,
       ci.name AS city,
       ci.population
FROM country co
JOIN city ci ON co.code = ci.countrycode
WHERE co.continent = 'Asia'
  AND ci.population >= 5000000
ORDER BY ci.population DESC;
```

**국가와 수도, 공식 언어** — 3개 테이블 연결

```sql
SELECT co.name AS country_name,
       ci.name AS capital_city,
       cl."Language"
FROM country co
JOIN city ci ON co.capital = ci.id
JOIN countrylanguage cl ON co.code = cl.countrycode
WHERE cl.isofficial = 'T';
```

- 컬럼명이 대문자로 정의된 `"Language"`는 큰따옴표로 감싸야 한다.

## 예제: dvdrental

### 고객 정보를 한 단계씩 늘리기

`customer → address → city → country`로 이어지는 1:N 체인이다. 테이블을 하나 붙일 때마다 컬럼도 하나씩 늘려가며 확인하면 실수를 줄일 수 있다.

```sql
-- 이름, 이메일, 주소, 도시, 국가
SELECT c.first_name,
       c.last_name,
       c.email,
       a.address,
       ci.city,
       co.country
FROM customer c
JOIN address a ON c.address_id = a.address_id
JOIN city ci ON a.city_id = ci.city_id
JOIN country co ON ci.country_id = co.country_id;
```

**London에 사는 고객**

```sql
SELECT c.first_name, c.last_name, c.email, a.address, ci.city
FROM customer c
JOIN address a ON c.address_id = a.address_id
JOIN city ci ON a.city_id = ci.city_id
WHERE ci.city = 'London';
```

**도시별 고객 수**

```sql
SELECT ci.city, COUNT(*) AS customer_count
FROM customer c
JOIN address a ON c.address_id = a.address_id
JOIN city ci ON a.city_id = ci.city_id
GROUP BY ci.city_id, ci.city
ORDER BY COUNT(*) DESC;
```

- 같은 이름의 도시가 여러 나라에 있을 수 있으므로 `ci.city`만이 아니라 PK인 `ci.city_id`도 `GROUP BY`에 넣는다.

### 배우 - 영화

**배우가 출연한 영화**

```sql
SELECT a.first_name, a.last_name, f.title
FROM actor a
JOIN film_actor fa ON a.actor_id = fa.actor_id
JOIN film f ON fa.film_id = f.film_id;
```

**배우별 출연 영화 수**

```sql
SELECT a.first_name,
       a.last_name,
       COUNT(fa.film_id) AS num_of_films
FROM actor a
JOIN film_actor fa ON a.actor_id = fa.actor_id
GROUP BY a.actor_id, a.first_name, a.last_name
ORDER BY num_of_films;
```

**영화별 출연 배우 수**

```sql
SELECT f.title, COUNT(fa.actor_id) AS actor_count
FROM film f
JOIN film_actor fa ON f.film_id = fa.film_id
GROUP BY f.film_id;
```

- `SELECT`에 `f.title`이 있는데 `GROUP BY`에는 `f.film_id`만 있어도 PostgreSQL은 허용한다. PK로 묶으면 같은 행의 다른 컬럼이 하나로 정해지기 때문이다. 다른 DBMS에서는 오류가 날 수 있어 `f.title`도 함께 쓰는 편이 안전하다.

**영화의 카테고리** — `film`과 `category`는 M:N이라 `film_category`를 거친다.

```sql
SELECT f.title, c.name AS category
FROM film f
JOIN film_category fc ON f.film_id = fc.film_id
JOIN category c ON fc.category_id = c.category_id
ORDER BY c.name;
```

**카테고리별 영화 수**

```sql
SELECT c.name AS category,
       COUNT(f.film_id) AS film_count
FROM category c
JOIN film_category fc ON c.category_id = fc.category_id
JOIN film f ON fc.film_id = f.film_id
GROUP BY c.name
ORDER BY film_count DESC;
```

**배우가 출연한 영화를 카테고리와 함께** — 5개 테이블 연결

```sql
SELECT a.first_name,
       a.last_name,
       f.title,
       c.name AS category
FROM actor a
JOIN film_actor fa ON a.actor_id = fa.actor_id
JOIN film f ON fa.film_id = f.film_id
JOIN film_category fc ON f.film_id = fc.film_id
JOIN category c ON fc.category_id = c.category_id;
```

### JOIN + GROUP BY + HAVING

집계 결과로 거를 때는 `WHERE`가 아니라 `HAVING`을 쓴다.

**출연 영화가 30편 이상인 배우**

```sql
SELECT a.first_name,
       a.last_name,
       COUNT(fa.film_id) AS film_count
FROM actor a
JOIN film_actor fa ON a.actor_id = fa.actor_id
GROUP BY a.actor_id, a.first_name, a.last_name
HAVING COUNT(fa.film_id) >= 30
ORDER BY film_count DESC;
```

**출연 배우가 10명 이상인 영화**

```sql
SELECT f.title,
       COUNT(fa.actor_id) AS actor_count
FROM film f
JOIN film_actor fa ON f.film_id = fa.film_id
GROUP BY f.film_id, f.title
HAVING COUNT(fa.actor_id) >= 10
ORDER BY actor_count DESC;
```

## 정리

- `INNER JOIN`은 일치하는 행만, `LEFT JOIN`은 왼쪽을 모두 유지한다. "짝이 없는 것"을 찾으려면 `LEFT JOIN` + `WHERE 오른쪽PK IS NULL`.
- M:N 관계는 연관 테이블을 사이에 두고 `JOIN`을 두 번 한다.
- 1:N 조인은 N쪽 행 수만큼 결과가 늘어난다. 그대로 `COUNT`하면 중복 집계될 수 있어 무엇을 세는지 먼저 정해야 한다.
- `LEFT JOIN`에서 오른쪽 테이블 조건은 `ON`에 쓰면 왼쪽을 유지하고, `WHERE`에 쓰면 짝 없는 행이 사라진다.
- `JOIN`이 길어질수록 별칭(`c`, `a`, `ci`)을 일관되게 쓰고, 테이블을 한 단계씩 붙여가며 확인한다.
