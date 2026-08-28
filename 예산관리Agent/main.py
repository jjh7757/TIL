from api import run_agent


def main():
    print("개인 예산 관리 Agent입니다. 자연어로 거래를 등록/검색/수정하거나 예산을 물어보세요. (종료: exit)")
    while True:
        user_input = input("\n> ").strip()
        if not user_input:
            continue
        if user_input == "exit":
            break

        result = run_agent(user_input)
        print(result["answer"] if result["ok"] else result["error"])


if __name__ == "__main__":
    main()
