from pprint import pprint
from sheets import (
    get_worksheet,
    add_transaction,
    read_transactions,
    read_budget,
    set_budget,
    get_remaining_budget,
    search_transactions,
    update_transaction,
    delete_transaction,
    save_monthly_report,
)
from api import run_agent


# ── 함수 직접 호출 테스트 (Gemini 없이) ──────────────────────

def test_add_transaction_direct():
    ws = get_worksheet("거래내역")
    거래_ID = add_transaction(ws, "지출", "식비", 8000, "저녁값")
    print("등록된 거래 ID:", 거래_ID)


def test_read_transactions_direct():
    ws = get_worksheet("거래내역")
    pprint(read_transactions(ws))


def test_set_budget_direct():
    ws_budget = get_worksheet("예산")
    result = set_budget(ws_budget, "식비", "2026-08", 300000)
    pprint(result)


def test_get_remaining_budget_direct():
    ws = get_worksheet("거래내역")
    ws_budget = get_worksheet("예산")
    result = get_remaining_budget(ws_budget, ws, "식비", "2026-08")
    pprint(result)


def test_get_remaining_budget_no_budget_set():
    # 존재하지 않는 카테고리 예산 조회 → 에러 처리 확인
    ws = get_worksheet("거래내역")
    ws_budget = get_worksheet("예산")
    result = get_remaining_budget(ws_budget, ws, "존재하지않는카테고리", "2026-08")
    pprint(result)


def test_search_transactions_direct():
    ws = get_worksheet("거래내역")
    pprint(search_transactions(ws, 카테고리="식비"))


def test_update_transaction_direct():
    ws = get_worksheet("거래내역")
    거래_ID = add_transaction(ws, "지출", "카페", 5000, "카페")
    result = update_transaction(ws, 거래_ID, 금액=4500)
    pprint(result)


def test_update_transaction_not_found_direct():
    # 존재하지 않는 거래 ID 수정 시도 → 에러 처리 확인
    ws = get_worksheet("거래내역")
    result = update_transaction(ws, 999999, 금액=1000)
    pprint(result)


def test_delete_transaction_direct():
    ws = get_worksheet("거래내역")
    거래_ID = add_transaction(ws, "지출", "테스트삭제", 1000, "삭제될 거래")
    result = delete_transaction(ws, 거래_ID)
    pprint(result)


def test_delete_transaction_not_found_direct():
    # 존재하지 않는 거래 ID 삭제 시도 → 에러 처리 확인
    ws = get_worksheet("거래내역")
    result = delete_transaction(ws, 999999)
    pprint(result)


def test_add_transaction_invalid_amount_direct():
    # 음수 금액 등록 시도 → 검증 에러 확인
    ws = get_worksheet("거래내역")
    try:
        add_transaction(ws, "지출", "식비", -5000, "잘못된 금액")
        print("버그: 에러가 발생하지 않았습니다")
    except ValueError as e:
        print("정상적으로 거부됨:", e)


def test_set_budget_invalid_month_direct():
    # 잘못된 월 형식 → 검증 에러 확인
    ws_budget = get_worksheet("예산")
    try:
        set_budget(ws_budget, "식비", "2026/08", 300000)
        print("버그: 에러가 발생하지 않았습니다")
    except ValueError as e:
        print("정상적으로 거부됨:", e)


def test_update_transaction_invalid_id_direct():
    # 숫자가 아닌 거래 ID → 검증 에러 확인
    ws = get_worksheet("거래내역")
    try:
        update_transaction(ws, "abc", 금액=1000)
        print("버그: 에러가 발생하지 않았습니다")
    except ValueError as e:
        print("정상적으로 거부됨:", e)


def test_update_transaction_invalid_date_direct():
    # 잘못된 날짜 형식 → 검증 에러 확인
    ws = get_worksheet("거래내역")
    try:
        update_transaction(ws, 1, 거래_날짜="2026/08/28")
        print("버그: 에러가 발생하지 않았습니다")
    except ValueError as e:
        print("정상적으로 거부됨:", e)


def test_save_monthly_report_direct():
    ws = get_worksheet("거래내역")
    result = save_monthly_report(ws, "2026-08")
    pprint(result)


# ── 자연어 Agent 테스트 (Gemini 경유) ────────────────────────

def test_agent_add_transaction():
    result = run_agent("오늘 점심으로 12000원 썼어")
    print(result["answer"] if result["ok"] else result["error"])
    print("\n도구 실행 기록:", [log["tool"] for log in result["tool_logs"]])


def test_agent_set_budget():
    result = run_agent("이번 달 식비 예산을 30만원으로 설정해줘")
    print(result["answer"] if result["ok"] else result["error"])
    print("\n도구 실행 기록:", [log["tool"] for log in result["tool_logs"]])


def test_agent_get_remaining_budget():
    result = run_agent("이번 달 식비 예산 얼마나 남았어?")
    print(result["answer"] if result["ok"] else result["error"])
    print("\n도구 실행 기록:", [log["tool"] for log in result["tool_logs"]])


def test_agent_search_and_update():
    # 검색 → 수정으로 이어지는 연속 도구 호출 시나리오
    ws = get_worksheet("거래내역")
    add_transaction(ws, "지출", "카페", 5000, "카페")
    result = run_agent("오늘 카페에서 쓴 금액을 4500원으로 수정해줘")
    print(result["answer"] if result["ok"] else result["error"])
    print("\n도구 실행 기록:", [log["tool"] for log in result["tool_logs"]])


def test_agent_update_nonexistent():
    # 존재하지 않는 거래 수정 요청 → 오류 처리 확인
    result = run_agent("거래 ID 999999번 금액을 1000원으로 수정해줘")
    print(result["answer"] if result["ok"] else result["error"])
    print("\n도구 실행 기록:", [log["tool"] for log in result["tool_logs"]])


def test_agent_delete_transaction():
    ws = get_worksheet("거래내역")
    거래_ID = add_transaction(ws, "지출", "테스트삭제", 1000, "삭제될 거래")
    result = run_agent(f"거래 ID {거래_ID}번 삭제해줘. 삭제하는 거 확인했어.")
    print(result["answer"] if result["ok"] else result["error"])
    print("\n도구 실행 기록:", [log["tool"] for log in result["tool_logs"]])


def test_agent_delete_nonexistent():
    result = run_agent("거래 ID 999999번 삭제해줘. 확인했어.")
    print(result["answer"] if result["ok"] else result["error"])
    print("\n도구 실행 기록:", [log["tool"] for log in result["tool_logs"]])


def test_agent_invalid_budget_amount():
    # 잘못된(음수) 예산 금액 요청 → 검증 에러가 사용자에게 어떻게 전달되는지 확인
    result = run_agent("이번 달 식비 예산을 -50000원으로 설정해줘")
    print(result["answer"] if result["ok"] else result["error"])
    print("\n도구 실행 기록:", [log["tool"] for log in result["tool_logs"]])


def test_agent_save_monthly_report():
    result = run_agent("이번 달 거래 내역 보고서로 저장해줘")
    print(result["answer"] if result["ok"] else result["error"])
    print("\n도구 실행 기록:", [log["tool"] for log in result["tool_logs"]])


def get_existing_transaction_ids() -> set:
    ws = get_worksheet("거래내역")
    return {int(row["거래 ID"]) for row in read_transactions(ws) if str(row["거래 ID"]).strip() != ""}


def cleanup_new_transactions(baseline_ids: set):
    ws = get_worksheet("거래내역")
    current_ids = {int(row["거래 ID"]) for row in read_transactions(ws) if str(row["거래 ID"]).strip() != ""}
    new_ids = current_ids - baseline_ids

    if not new_ids:
        print("정리할 테스트 데이터가 없습니다.")
        return

    for 거래_ID in sorted(new_ids):
        result = delete_transaction(ws, 거래_ID)
        print(f"거래 ID {거래_ID} 삭제:", result)


def run_all_tests():
    baseline_ids = get_existing_transaction_ids()

    tests = [
        test_add_transaction_direct,
        test_read_transactions_direct,
        test_set_budget_direct,
        test_get_remaining_budget_direct,
        test_get_remaining_budget_no_budget_set,
        test_search_transactions_direct,
        test_update_transaction_direct,
        test_update_transaction_not_found_direct,
        test_delete_transaction_direct,
        test_delete_transaction_not_found_direct,
        test_add_transaction_invalid_amount_direct,
        test_set_budget_invalid_month_direct,
        test_update_transaction_invalid_id_direct,
        test_update_transaction_invalid_date_direct,
        test_save_monthly_report_direct,
        test_agent_add_transaction,
        test_agent_set_budget,
        test_agent_get_remaining_budget,
        test_agent_search_and_update,
        test_agent_update_nonexistent,
        test_agent_delete_transaction,
        test_agent_delete_nonexistent,
        test_agent_invalid_budget_amount,
        test_agent_save_monthly_report,
    ]
    for test in tests:
        print(f"\n{'=' * 20} {test.__name__} {'=' * 20}")
        test()

    print(f"\n{'=' * 20} cleanup {'=' * 20}")
    cleanup_new_transactions(baseline_ids)


if __name__ == "__main__":
    run_all_tests()
