# langgraph_mini — 계좌 이체 서비스 설계/구현

코드: [jjh7757/langgraph_mini](https://github.com/jjh7757/langgraph_mini)

Spring(Java) 개발 경험을 바탕으로 계좌 이체 서비스를 직접 설계하고, Python(3.13, `typing.Protocol`)으로 옮겨 구현 중인 미니 프로젝트. 도메인/Repository/Service 계층 분리와 TDD를 실습하는 게 목적이라, 기능 자체보다 설계 결정 하나하나에 근거를 남기는 데 집중했다.

## 초기 설계 리뷰 — God Object와 화살표 의미

손으로 그린 첫 다이어그램은 `AccountServiceImpl` 하나가 계좌 조회·잔액 합산·거래 내역 조회·즉시/조건부/분할 이체·별명 변경 7개 메서드를 전부 구현하는 구조였다. 여기서 두 가지를 지적하고 고쳤다.

- **인터페이스 분리(ISP)와 구현체 분리는 별개 문제**: `AccountService` 인터페이스를 Query/Transfer/Manage 셋으로 쪼개도, 구현체가 여전히 `AccountServiceImpl` 하나면 클래스 응집도는 그대로 낮다. 구현체도 인터페이스별로 3개(`AccountQueryServiceImpl` 등)로 나눠야 실제로 테스트 독립성·병렬 개발이 가능해진다.
- **"Use"와 "Implements"는 다른 화살표**: 구현 클래스가 인터페이스를 구현하는 관계(속 빈 삼각형)와 한 클래스가 다른 걸 그냥 갖다 쓰는 의존 관계(열린 화살표)를 같은 점선 화살표로 뭉뚱그리면 나중에 구분이 안 된다.
- **Repository 1개 : Service 3개는 문제가 아님**: 여러 서비스가 같은 Repository를 참조하는 건 Repository 책임이 "Account 하나를 영속화하는 것"으로 좁고 명확하면 정상. 반대로 Repository가 서비스별 전용 메서드로 계속 커지면 그때 CQRS 스타일 분리를 고려.

## Java 인터페이스를 Python으로 그대로 옮기면 안 되는 이유

Python엔 `interface` 키워드가 없고, 목적에 따라 세 가지 방식이 있다.

| | Java `interface` | `abc.ABC` | `typing.Protocol` |
|---|---|---|---|
| 강제 시점 | 컴파일 타임 | 런타임(인스턴스화 시) | 정적 타입 검사기(선택) |
| 명시적 상속 필요 | O | O | X (메서드 시그니처만 맞으면 됨) |

`Protocol`을 쓰면 `class DefaultAccountQueryService(AccountQueryService):`처럼 상속을 선언하지 않아도 되고, 구현체 이름에 Java식 `Impl` 접미사를 붙이는 관행도 버렸다(`DefaultAccountQueryService`, `SqlAccountRepository`처럼 역할이 드러나는 이름 사용). 구현 관계는 `implements` 대신 `satisfies`(구조적으로 만족)로 표현.

## 계층별 책임 — Domain / Repository / Service

- **Domain(`Account`)**: 자기 상태를 스스로 검증하며 바꾼다(`withdraw`/`deposit`/`rename`). 저장소를 몰라야 하고, 필드 직접 대입 대신 이 메서드들을 통해서만 상태가 바뀌어야 한다는 불변식.
- **Repository**: 순수 저장/조회만. `save()` 안에서 도메인 메서드(`withdraw` 등)를 호출하면 안 된다 — 반대로 도메인 로직을 먼저 실행하고 그 결과를 Repository가 그대로 저장하는 순서.
- **Service**: 위 둘을 조합하는 흐름만 지휘 (`repo.find_by_id` → domain 메서드 호출 → `repo.save`). 여러 계좌를 다루는 이체 같은 로직도 여기서 순서를 정한다.

## TDD로 실제로 잡은 버그들

구현하면서 겪은 버그와 pytest가 어떻게 잡아냈는지 기록.

- `find_by_id(self._accounts["{account_id}"])`처럼 f-string을 빼먹고 변수명을 문자 그대로의 문자열로 취급 — dict에 없는 고정 키를 찾으니 항상 `KeyError`
- `save()`가 존재 여부를 먼저 확인하려고 자기 자신인 `find_by_id`를 호출 — 신규 계좌 저장 시 `AccountNotFoundError`로 항상 실패 (dict 대입 한 줄이면 되는 걸 복잡하게 만든 사례)
- `self._accounts.get(account.id) = account` — 함수 호출 결과에 대입하려 해서 `SyntaxError`
- `self.get_account(self, account_id)` — 인스턴스 메서드를 호출할 때 `self`를 또 넘김. `obj.method(args)`는 `type(obj).method(obj, args)`와 같다는 걸 헷갈린 경우
- 이체 로직에서 `from_account.deposit()` / `to_account.withdraw()`처럼 출금·입금이 뒤바뀜 — 방향이 반대인 이체가 조용히 성공하는 버그
- `withdraw`/`deposit`에 음수를 넣으면 부호가 뒤집혀 반대 효과가 나는 경우 — 두 메서드 모두 `amount <= 0` 검증 추가로 막음

일부러 예전 버그 버전으로 되돌려서 `uv run pytest`를 다시 돌려보고, 통과하던 테스트가 바로 빨간불로 바뀌는 걸 확인 — 테스트가 "코드가 맞다"를 증명하는 게 아니라 "이 시나리오는 이 결과가 나온다"를 계속 지켜주는 안전망이라는 걸 체감.

## 요구사항 필드 하나에도 설계 의도가 있다

`Account`에 `id` 대신 `account_id`+`owner_id`를 요구하는 스펙을 보고, 단순 필드 추가가 아니라 이후 요구사항의 전제 조건이라고 분석했다:

1. 계좌:소유자가 1:N이라는 관계 모델링을 강제
2. "이 요청자가 이 계좌 주인이 맞는가" 권한 검증을 나중에 넣을 여지
3. "내 계좌 총 잔액" 같은 조회가 계좌 id 목록을 미리 알 필요 없이 `owner_id` 하나로 가능해짐

실제로 뒤이어 받은 전체 요구사항(계좌 조회/잔액 합산/거래 내역 조회/이체 3종/별명 변경)에서 이 분석이 대부분 들어맞아서, `get_total_balance`·`get_accounts`를 `account_ids` 목록이 아니라 `owner_id` 하나로 받도록 다시 설계했다.

## 요구사항 반영 — Transaction/Card 재설계

"거래 내역 조회(카드 결제 시 사용 카드 표시)" 요구사항을 보고 `Transaction(from_id, to_id, amount)` 하나로는 부족하다는 걸 확인. 이체 한 건이 계좌마다 다른 관점(출금/입금)의 내역으로 보여야 해서, 이체 1건당 `TRANSFER_OUT`/`TRANSFER_IN` 두 줄을 계좌별로 남기는 구조로 바꾸고, `Card` 도메인과 `CardRepository`를 별도로 분리했다. Repository는 여전히 필터링을 하지 않고 전체 조회만 담당하며, 기간·금액·유형 필터링과 최근순 정렬은 Service 계층 책임으로 남겼다 — "이번 달"/"이번 주" 같은 자연어를 실제 날짜로 바꾸는 것도 이 서비스가 아니라 LangGraph 기반 상위 에이전트가 할 일로 경계를 그었다.

조건부 이체는 "승인 후 처리 + 실행 전 잔액이 달라지면 재승인"이라는 요구사항을 만족시키려면 계산과 실행 사이에 시간차가 있어야 한다는 점에서, 단일 메서드 호출이 아니라 `calculate_conditional_transfer`(계산만, 잔액 스냅샷 포함) → `confirm_conditional_transfer`(실행 시점 잔액이 스냅샷과 다르면 재승인 요구) 2단계로 설계했다.
