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

ws = get_worksheet("거래내역")
ws_budget = get_worksheet("예산")

add_transaction_tool = {
    "type": "function",
    "name": "add_transaction",
    "description": "구글시트에 거래 내역을 한 줄 추가합니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "거래_유형": {"type": "string", "description": "거래 유형. 예: 수입, 지출"},
            "카테고리": {"type": "string", "description": "거래 카테고리. 예: 식비, 월급"},
            "금액": {"type": "integer", "description": "거래 금액"},
            "설명": {"type": "string", "description": "거래에 대한 간단한 설명"},
        },
        "required": ["거래_유형", "카테고리", "금액"],
        "additionalProperties": False,
    },
}

read_transactions_tool = {
    "type": "function",
    "name": "read_transactions",
    "description": "구글시트에 저장된 모든 거래 내역을 조회합니다.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
}

read_budget_tool = {
    "type": "function",
    "name": "read_budget",
    "description": "구글시트에 저장된 카테고리별 월 예산 목록을 조회합니다.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
}

set_budget_tool = {
    "type": "function",
    "name": "set_budget",
    "description": "카테고리와 월을 지정해 예산 금액을 설정하거나 수정합니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "카테고리": {"type": "string", "description": "예산을 설정할 카테고리. 예: 식비"},
            "월": {"type": "string", "description": "예산을 설정할 월. 'YYYY-MM' 형식. 예: 2026-08"},
            "예산금액": {
                "type": "integer",
                "description": "설정할 예산 총액. add_transaction의 '금액'(개별 거래 금액)과는 다른, 카테고리의 월간 예산 한도를 뜻함",
            },
        },
        "required": ["카테고리", "월", "예산금액"],
        "additionalProperties": False,
    },
}

get_remaining_budget_tool = {
    "type": "function",
    "name": "get_remaining_budget",
    "description": "카테고리와 월을 지정해 설정된 예산과 해당 월 지출액을 비교하여 남은 예산을 조회합니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "카테고리": {"type": "string", "description": "조회할 카테고리. 예: 식비"},
            "월": {"type": "string", "description": "조회할 월. 'YYYY-MM' 형식. 예: 2026-08"},
        },
        "required": ["카테고리", "월"],
        "additionalProperties": False,
    },
}

search_transactions_tool = {
    "type": "function",
    "name": "search_transactions",
    "description": "카테고리, 거래 날짜, 설명 조건으로 거래 내역을 검색합니다. 각 조건은 생략 가능하며, 지정한 조건만 필터링에 사용됩니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "카테고리": {"type": "string", "description": "검색할 카테고리. 예: 식비 (생략 가능)"},
            "거래_날짜": {"type": "string", "description": "검색할 거래 날짜. 'YYYY-MM-DD' 형식. 예: 2026-08-27 (생략 가능)"},
            "설명": {"type": "string", "description": "설명에 포함된 문자열로 검색. 예: 카페 (생략 가능)"},
        },
        "required": [],
        "additionalProperties": False,
    },
}

update_transaction_tool = {
    "type": "function",
    "name": "update_transaction",
    "description": "거래 ID로 특정 거래를 찾아 값을 수정합니다. 수정할 필드만 지정하면 되고, 해당 ID가 없으면 오류를 반환합니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "거래_ID": {"type": "integer", "description": "수정할 거래의 ID. search_transactions로 먼저 찾아야 함"},
            "거래_유형": {"type": "string", "description": "거래 유형. 예: 수입, 지출 (생략 가능)"},
            "카테고리": {"type": "string", "description": "거래 카테고리. 예: 식비 (생략 가능)"},
            "금액": {"type": "integer", "description": "거래 금액 (생략 가능)"},
            "설명": {"type": "string", "description": "거래 설명 (생략 가능)"},
            "거래_날짜": {"type": "string", "description": "거래 날짜. 'YYYY-MM-DD' 형식 (생략 가능)"},
        },
        "required": ["거래_ID"],
        "additionalProperties": False,
    },
}

delete_transaction_tool = {
    "type": "function",
    "name": "delete_transaction",
    "description": "거래 ID로 특정 거래를 찾아 삭제합니다. 해당 ID가 없으면 오류를 반환합니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "거래_ID": {"type": "integer", "description": "삭제할 거래의 ID"},
        },
        "required": ["거래_ID"],
        "additionalProperties": False,
    },
}

save_monthly_report_tool = {
    "type": "function",
    "name": "save_monthly_report",
    "description": "지정한 월의 거래 내역을 요약과 표로 정리한 Markdown 보고서 파일로 저장합니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "월": {"type": "string", "description": "보고서를 생성할 월. 'YYYY-MM' 형식. 예: 2026-08"},
        },
        "required": ["월"],
        "additionalProperties": False,
    },
}

TOOL_LIST = [
    add_transaction_tool,
    read_transactions_tool,
    read_budget_tool,
    set_budget_tool,
    get_remaining_budget_tool,
    search_transactions_tool,
    update_transaction_tool,
    delete_transaction_tool,
    save_monthly_report_tool,
]

TOOL_FUNCTIONS = {
    "add_transaction": lambda args: add_transaction(ws, **args),
    "read_transactions": lambda args: read_transactions(ws),
    "read_budget": lambda args: read_budget(ws_budget),
    "set_budget": lambda args: set_budget(ws_budget, **args),
    "get_remaining_budget": lambda args: get_remaining_budget(ws_budget, ws, **args),
    "search_transactions": lambda args: search_transactions(ws, **args),
    "update_transaction": lambda args: update_transaction(ws, **args),
    "delete_transaction": lambda args: delete_transaction(ws, **args),
    "save_monthly_report": lambda args: save_monthly_report(ws, **args),
}