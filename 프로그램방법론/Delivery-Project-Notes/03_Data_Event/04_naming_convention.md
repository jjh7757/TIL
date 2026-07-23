# 용어와 네이밍 컨벤션

## 네이밍 컨벤션이란?

프로젝트에서 같은 대상을 같은 이름으로 표현하기 위한 공통 규칙입니다.

## 공식 용어

| 한글 공식 용어 | 영문 기준 이름 | 고유 번호 |
|---|---|---|
| 고객 | `customer` | `customer_id` |
| 음식점 | `restaurant` | `restaurant_id` |
| 메뉴 | `menu` | `menu_id` |
| 추천 결과 | `recommendation` | `recommendation_id` |
| 장바구니 | `cart` | `cart_id` |
| 주문 | `order` | `order_id` |
| 결제 | `payment` | `payment_id` |

## 이름 규칙

- 고유 번호는 이름 뒤에 `_id`를 붙입니다.
- 여러 영문 단어는 소문자와 밑줄을 사용하는 `snake_case`로 작성합니다.
- 이벤트는 이미 발생한 사건을 과거형으로 작성합니다.
- 같은 대상은 문서, 데이터, 이벤트에서 같은 뿌리 단어를 사용합니다.
- 합의하지 않은 줄임말은 사용하지 않습니다.

## 이벤트 이름 예시

- `recommendation_requested`
- `recommendation_created`
- `recommendation_failed`
- `cart_item_added`
- `order_created`
- `payment_completed`
- `payment_failed`