import gspread
import pandas as pd
import os
import re
from datetime import date, datetime
from google.oauth2.service_account import Credentials
from pprint import pprint
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
if not SPREADSHEET_ID:
    raise ValueError(".env 파일에 SPREADSHEET_ID를 설정해 주세요.")

def get_worksheet(sheet_name):

    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    gc = gspread.authorize(creds)

    # URL 또는 key로 시트 열기
    sh = gc.open_by_key(SPREADSHEET_ID)   # URL의 /d/와 /edit 사이 문자열
    worksheet = sh.worksheet(sheet_name)         # 시트 탭 이름
    return worksheet

def validate_amount(금액):
    if isinstance(금액, bool) or not isinstance(금액, (int, float)):
        raise ValueError(f"금액은 숫자여야 합니다: {금액}")
    if 금액 <= 0:
        raise ValueError(f"금액은 0보다 커야 합니다: {금액}")


def validate_date(거래_날짜):
    try:
        date.fromisoformat(str(거래_날짜))
    except ValueError:
        raise ValueError(f"날짜 형식이 올바르지 않습니다. 'YYYY-MM-DD' 형식으로 입력하세요: {거래_날짜}")


def validate_month(월):
    if not re.fullmatch(r"\d{4}-\d{2}", str(월)):
        raise ValueError(f"월 형식이 올바르지 않습니다. 'YYYY-MM' 형식으로 입력하세요: {월}")
    try:
        datetime.strptime(str(월), "%Y-%m")
    except ValueError:
        raise ValueError(f"월 형식이 올바르지 않습니다. 'YYYY-MM' 형식으로 입력하세요: {월}")


def validate_transaction_id(거래_ID):
    try:
        int(거래_ID)
    except (TypeError, ValueError):
        raise ValueError(f"거래 ID는 숫자여야 합니다: {거래_ID}")


def get_next_id(ws) -> int:
    ids = [int(row["거래 ID"]) for row in ws.get_all_records() if str(row["거래 ID"]).strip() != ""]
    if not ids:
        return 1
    return max(ids) + 1


def add_transaction(ws, 거래_유형, 카테고리, 금액, 설명):
    validate_amount(금액)
    거래_ID = get_next_id(ws)
    거래_날짜 = date.today().isoformat()
    ws.append_row([거래_ID, 거래_유형, 카테고리, 금액, 설명, 거래_날짜])
    return 거래_ID


def read_transactions(ws) -> list[dict]:
    return ws.get_all_records()   # 헤더를 key로 쓰는 딕셔너리 리스트


def read_budget(ws) -> list[dict]:
    return ws.get_all_records()   # 예산 시트 컬럼: 카테고리, 월, 예산금액 (가정)


def set_budget(ws, 카테고리, 월, 예산금액):
    validate_month(월)
    validate_amount(예산금액)
    records = ws.get_all_records()
    for i, row in enumerate(records, start=2):  # 1행은 헤더
        if row["카테고리"] == 카테고리 and str(row["월"]) == str(월):
            ws.update_cell(i, 3, 예산금액)  # 3번째 열 = 예산금액
            return {"ok": True, "action": "updated", "카테고리": 카테고리, "월": 월, "예산금액": 예산금액}
    ws.append_row([카테고리, 월, 예산금액])
    return {"ok": True, "action": "added", "카테고리": 카테고리, "월": 월, "예산금액": 예산금액}


def get_remaining_budget(ws_budget, ws_transactions, 카테고리, 월):
    validate_month(월)
    예산금액 = None
    for row in ws_budget.get_all_records():
        if row["카테고리"] == 카테고리 and str(row["월"]) == str(월):
            예산금액 = int(row["예산금액"])
            break

    if 예산금액 is None:
        return {"ok": False, "error": f"{월} {카테고리} 예산이 설정되어 있지 않습니다."}

    사용금액 = sum(
        int(row["금액"])
        for row in ws_transactions.get_all_records()
        if str(row["거래 ID"]).strip() != ""
        and row["카테고리"] == 카테고리
        and row["거래 유형"] == "지출"
        and str(row["거래 날짜"]).startswith(월)
    )

    return {
        "ok": True,
        "카테고리": 카테고리,
        "월": 월,
        "예산금액": 예산금액,
        "사용금액": 사용금액,
        "남은예산": 예산금액 - 사용금액,
    }

def search_transactions(ws, 카테고리=None, 거래_날짜=None, 설명=None) -> list[dict]:
    if 거래_날짜 is not None:
        validate_date(거래_날짜)
    results = []
    for row in ws.get_all_records():
        if str(row["거래 ID"]).strip() == "":
            continue
        if 카테고리 is not None and row["카테고리"] != 카테고리:
            continue
        if 거래_날짜 is not None and str(row["거래 날짜"]) != str(거래_날짜):
            continue
        if 설명 is not None and 설명 not in str(row["설명"]):
            continue
        results.append(row)
    return results


TRANSACTION_COLUMN_INDEX = {
    "거래_유형": 2,
    "카테고리": 3,
    "금액": 4,
    "설명": 5,
    "거래_날짜": 6,
}


def update_transaction(ws, 거래_ID, 거래_유형=None, 카테고리=None, 금액=None, 설명=None, 거래_날짜=None):
    validate_transaction_id(거래_ID)
    if 금액 is not None:
        validate_amount(금액)
    if 거래_날짜 is not None:
        validate_date(거래_날짜)

    updates = {
        "거래_유형": 거래_유형,
        "카테고리": 카테고리,
        "금액": 금액,
        "설명": 설명,
        "거래_날짜": 거래_날짜,
    }

    for i, row in enumerate(ws.get_all_records(), start=2):  # 1행은 헤더
        if str(row["거래 ID"]).strip() == "":
            continue
        if int(row["거래 ID"]) == int(거래_ID):
            for field, value in updates.items():
                if value is not None:
                    ws.update_cell(i, TRANSACTION_COLUMN_INDEX[field], value)
            return {"ok": True, "거래_ID": 거래_ID}

    return {"ok": False, "error": f"거래 ID {거래_ID}를 찾을 수 없습니다."}


def delete_transaction(ws, 거래_ID):
    validate_transaction_id(거래_ID)
    for i, row in enumerate(ws.get_all_records(), start=2):  # 1행은 헤더
        if str(row["거래 ID"]).strip() == "":
            continue
        if int(row["거래 ID"]) == int(거래_ID):
            ws.delete_rows(i)
            return {"ok": True, "거래_ID": 거래_ID}

    return {"ok": False, "error": f"거래 ID {거래_ID}를 찾을 수 없습니다."}


def generate_monthly_report(ws, 월) -> str:
    validate_month(월)
    transactions = [
        row for row in ws.get_all_records()
        if str(row["거래 ID"]).strip() != "" and str(row["거래 날짜"]).startswith(월)
    ]

    총수입 = sum(row["금액"] for row in transactions if row["거래 유형"] == "수입")
    총지출 = sum(row["금액"] for row in transactions if row["거래 유형"] == "지출")

    lines = [
        f"# {월} 거래 내역 보고서",
        "",
        f"- 총 수입: {총수입:,}원",
        f"- 총 지출: {총지출:,}원",
        f"- 순액: {총수입 - 총지출:,}원",
        "",
        "| 거래 ID | 유형 | 카테고리 | 금액 | 설명 | 날짜 |",
        "|---|---|---|---|---|---|",
    ]
    for row in sorted(transactions, key=lambda r: str(r["거래 날짜"])):
        lines.append(
            f"| {row['거래 ID']} | {row['거래 유형']} | {row['카테고리']} | "
            f"{row['금액']:,}원 | {row['설명']} | {row['거래 날짜']} |"
        )

    return "\n".join(lines)


def save_monthly_report(ws, 월) -> dict:
    report = generate_monthly_report(ws, 월)
    파일명 = f"report_{월}.md"
    with open(파일명, "w", encoding="utf-8") as f:
        f.write(report)
    return {"ok": True, "파일명": 파일명, "월": 월}


def test():
    ws = get_worksheet("거래내역")
    add_transaction(ws, "test", "일반", 5000, "test")
    list = read_transactions(ws)

    pprint(list)