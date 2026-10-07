# SQL 뷰(View)

저장된 `SELECT` 쿼리를 테이블처럼 조회할 수 있게 만든 DB 객체인 뷰의 개념, 장단점, 생성·삭제, 활용 예제를 정리했습니다.
복잡한 조인은 [SQL JOIN](SQL_JOIN.md)을 참고하세요.

> PostgreSQL 기준. 예제 DB는 `dvdrental`입니다.

## 뷰란

- 뷰는 **쿼리 자체를 저장**한 객체다. 조회 결과 데이터를 따로 저장하지 않는다.
- 뷰를 조회할 때마다 원본 테이블의 데이터를 바탕으로 결과를 만들어 반환한다. 그래서 원본이 바뀌면 뷰 결과도 바뀐다.
- 복잡한 쿼리를 단순화하고, 필요한 행과 컬럼만 제공하는 데 쓴다.

## 장단점

| 구분 | 내용 |
|------|------|
| 보안성 | 특정 컬럼·행만 공개해 민감한 정보 노출을 막는다 |
| 편의성 | 반복되는 복잡한 조인·서브쿼리를 미리 정의해 재사용한다 |
| 제한사항 | 인덱스를 직접 가질 수 없다 |
| 제한사항 | 단순한 뷰는 삽입·수정·삭제가 가능하지만, 조인·집계 등을 포함한 뷰는 기본적으로 읽기 전용이다 |

## 생성과 삭제

```sql
CREATE VIEW view_name AS
SELECT column1, column2
FROM table_name
WHERE condition;

DROP VIEW view_name;
```

- `DROP VIEW`는 뷰 정의만 지운다. **원본 테이블 데이터는 영향받지 않는다.**
- 생성한 뷰는 테이블처럼 `SELECT ... FROM view_name`으로 조회한다.

## 활용

### 보안 및 접근 제어

원본 테이블의 직접 조회 권한은 제한하고 **뷰에만 조회 권한을 부여**하면 필요한 정보만 공개할 수 있다.

```sql
-- 이름·이메일은 빼고 고객 ID와 활성화 여부만 노출
CREATE VIEW customer_status AS
SELECT customer_id, activebool
FROM customer;

SELECT * FROM customer_status;
```

### 복잡한 조인 단순화

영화 제목과 카테고리명을 결합한 뷰. 매번 3개 테이블을 조인하지 않고 뷰만 조회하면 된다.

```sql
CREATE VIEW film_with_category AS
SELECT film.title, category.name AS category_name
FROM film
JOIN film_category ON film.film_id = film_category.film_id
JOIN category ON category.category_id = film_category.category_id;

SELECT title
FROM film_with_category
WHERE category_name = 'Action';
```

## 예제

**영화 제목과 출연 배우 이름 뷰**

```sql
CREATE VIEW film_actor_info AS
SELECT f.title, a.first_name, a.last_name
FROM film f
JOIN film_actor fa ON f.film_id = fa.film_id
JOIN actor a ON fa.actor_id = a.actor_id;

-- first_name이 'PENELOPE'인 배우의 출연 영화
SELECT title
FROM film_actor_info
WHERE first_name = 'PENELOPE';
```

뷰 없이 같은 결과를 내는 SQL. 뷰는 이 조인을 감춰주는 역할이다.

```sql
SELECT f.title
FROM film f
JOIN film_actor fa ON f.film_id = fa.film_id
JOIN actor a ON fa.actor_id = a.actor_id
WHERE a.first_name = 'PENELOPE';
```

**2005년 5월 대여 기록 뷰**

```sql
CREATE VIEW rental_may_2005 AS
SELECT *
FROM rental
WHERE rental_date >= '2005-05-01' AND rental_date < '2005-06-01';

-- 뷰와 customer를 조인해 고객 이름과 대여 일시 조회
SELECT c.first_name, c.last_name, r.rental_date
FROM rental_may_2005 r
JOIN customer c ON r.customer_id = c.customer_id;
```

- 뷰도 일반 테이블처럼 별칭을 붙여 다른 테이블과 `JOIN`할 수 있다.
- 기간 조건을 `>= 시작일 AND < 다음 달 1일`로 쓰면 월말 시각이 잘리지 않는다.

## 정리

- 뷰는 데이터가 아니라 **쿼리를 저장**한다. 조회할 때마다 원본을 읽는다.
- 용도는 두 가지: 공개 범위 제한(보안)과 반복 쿼리 단순화(편의).
- 조인·집계가 들어간 뷰는 읽기 전용이고, 뷰에는 인덱스를 직접 만들 수 없다.
