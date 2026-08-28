import json
import os
from datetime import datetime
from pprint import pprint

from dotenv import load_dotenv
from google import genai
from tools import TOOL_LIST, TOOL_FUNCTIONS


load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError(".env 파일에 GEMINI_API_KEY를 설정해 주세요.")

model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
client = genai.Client(api_key=api_key)
print("준비 완료 / 사용 모델:", model)

TOOL_CALL_LOG_FILE = "tool_call_log.jsonl"


def log_tool_call(entry: dict):
    entry_with_time = {**entry, "timestamp": datetime.now().isoformat()}
    with open(TOOL_CALL_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry_with_time, ensure_ascii=False) + "\n")


def execute_tool_call(step) -> dict:
    tool_function = TOOL_FUNCTIONS.get(step.name)
    if tool_function is None:
        return {"ok": False, "error": f"허용되지 않은 도구: {step.name}"}

    try:
        return tool_function(step.arguments)
    except TypeError as error:
        return {"ok": False, "error": f"잘못된 인자: {error}"}
    except ValueError as error:
        return {"ok": False, "error": str(error)}
    except Exception as error:
        return {"ok": False, "error": f"도구 실행 실패: {type(error).__name__}"}

def run_agent(user_input: str, max_turns: int = 5) -> dict:
    next_input = user_input
    previous_interaction_id = None
    logs = []

    for turn in range(1, max_turns + 1):
        request = {
            "model": model,
            "input": next_input,
            "tools": TOOL_LIST,
            "system_instruction": (
                "예산 관리자입니다. 사용자에 요청에 따라 거래 내용을 등록하거나 예산이 얼마 남았는지 알려주세요 "
                "도구 결과에 없는 정보는 없다고 말하세요. "
                "사용자가 거래 ID를 이미 알려준 경우에는 바로 update_transaction 또는 delete_transaction을 호출하세요. "
                "거래 ID를 모르고 날짜·카테고리·설명 등으로만 대상을 지칭한 경우에는 "
                "먼저 search_transactions로 검색해 거래 ID를 찾은 뒤 update_transaction 또는 delete_transaction을 호출하세요. "
                "검색 결과가 2개 이상이면 임의로 하나를 골라 수정하거나 삭제하지 말고, "
                "날짜·카테고리·설명 등 어떤 조건을 더 알려주면 특정할 수 있는지 사용자에게 되물어보세요. "
                "거래를 삭제하기 전에는 삭제할 거래의 내용을 사용자에게 확인받으세요."
            ),
            "store": True,
        }
        if previous_interaction_id is not None:
            request["previous_interaction_id"] = previous_interaction_id

        interaction = client.interactions.create(**request)
        function_calls = [step for step in interaction.steps if step.type == "function_call"]

        if not function_calls:
            return {
                "ok": True,
                "answer": interaction.output_text,
                "turns": turn,
                "tool_logs": logs,
            }

        next_input = []
        for step in function_calls:
            result = execute_tool_call(step)
            log_entry = {"turn": turn, "tool": step.name, "arguments": step.arguments, "result": result}
            logs.append(log_entry)
            log_tool_call(log_entry)
            next_input.append({
                "type": "function_result",
                "name": step.name,
                "call_id": step.id,
                "result": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            })

        previous_interaction_id = interaction.id

    return {
        "ok": False,
        "answer": None,
        "turns": max_turns,
        "tool_logs": logs,
        "error": "최대 반복 횟수를 초과했습니다.",
    }
