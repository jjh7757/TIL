# LangGraph 로깅 — print() 대신 logging 쓰기

프로그램 실행 중 발생한 일을 남긴 기록을 로그(log), 기록하는 작업을 로깅(logging)이라 한다. `print()`로도 실행 과정을 볼 수 있지만 출력이 많아지면 필요한 기록만 골라 보기 어렵다. Python 기본 모듈인 `logging`은 설정만으로 기록할 중요도·출력 형식·저장 위치를 조절할 수 있다.

## 로거, 핸들러, 포매터

- **로거(Logger)**: `logger.info()`처럼 로그를 기록하는 객체. `getLogger("이름")`으로 가져오며 같은 이름이면 같은 로거를 얻는다.
- **핸들러(Handler)**: 로그를 화면·파일 등 지정한 위치로 보낸다. 하나의 로거에 여러 핸들러를 연결할 수 있다.
- **포매터(Formatter)**: 시각·레벨·메시지 등 로그 표시 형식을 정한다. 핸들러에 연결해서 쓴다.

```python
logger = logging.getLogger("lesson.langgraph")
logger.setLevel(logging.INFO)
logger.propagate = False   # 상위(루트) 로거로 다시 전달하지 않음

for handler in logger.handlers[:]:   # 설정 셀을 다시 실행해도 중복 출력 안 되게
    logger.removeHandler(handler)
    handler.close()

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%H:%M:%S"
))
logger.addHandler(console_handler)
```

`.py` 파일에서는 보통 `logging.getLogger(__name__)`으로 모듈 이름을 로거 이름으로 쓴다. 출력 예: `14:30:00 | INFO | lesson.langgraph | 로깅 준비 완료`.

## 로그 레벨로 중요도 나누기

| 레벨 | 기록할 상황 |
|---|---|
| `DEBUG` | 검색 결과 개수 등 자세한 진단 정보 |
| `INFO` | 노드 시작, 완료, 선택한 경로 |
| `WARNING` | 검색 결과가 없어 안내 답변으로 전환 |
| `ERROR` | 외부 서비스 오류로 요청 처리 실패 |
| `CRITICAL` | 서비스 전체를 계속 운영하기 어려운 심각한 문제 |

중요도는 `DEBUG < INFO < WARNING < ERROR < CRITICAL` 순이다. 로거 레벨을 INFO로 두면 DEBUG만 걸러지고, WARNING으로 두면 WARNING부터 남는다. **설정하지 않은 기본 루트 로거의 기준은 WARNING**이라, 아무 설정 없이 `logging.info(...)`를 쓰면 조용히 안 찍히는 경우가 많다.

## 화면은 간단하게, 파일은 자세하게

로그는 **로거의 기준을 통과한 뒤, 각 핸들러의 기준도 통과해야** 출력된다. 즉 로거가 INFO로 막혀 있으면 파일 핸들러만 DEBUG로 낮춰도 DEBUG 기록은 남지 않는다 — 로거 레벨이 먼저 걸러내는 1차 필터, 핸들러 레벨이 목적지별 2차 필터다.

```python
logger.setLevel(logging.DEBUG)          # 1차: 로거 통과 기준
console_handler.setLevel(logging.INFO)  # 2차: 화면은 INFO까지만
file_handler.setLevel(logging.DEBUG)    # 2차: 파일은 DEBUG까지 모두
```

파일 핸들러는 `FileHandler(log_path, mode="a", encoding="utf-8")`로 만든다. `mode="a"`는 기존 기록 뒤에 이어 쓰고, 설정 셀을 다시 실행할 때는 기존 파일 핸들러를 제거·`close()`한 뒤 새로 연결해야 중복 저장을 막는다.

## 로그 파일 로테이션

`RotatingFileHandler`는 파일 크기를 기준으로 새 파일로 전환하고 이전 파일은 정해진 개수만 보관한다.

```python
file_handler = RotatingFileHandler(log_path, maxBytes=1024, backupCount=2, encoding="utf-8")
```

- `maxBytes`: 파일을 교체할 크기 기준(바이트)
- `backupCount`: 보관할 이전 파일 개수(현재 기록 중인 파일은 제외)

현재 기록은 `29-langgraph.log`, 이전 기록은 `.log.1`, `.log.2`에 저장되고 `.1`이 더 최근이다. 보관 개수를 넘으면 가장 오래된 파일부터 삭제된다.

## 오류 메시지와 traceback 기록하기

`logger.error()`는 메시지만 남긴다. `except` 블록 안에서 `logger.exception()`을 쓰면 ERROR 레벨 메시지와 함께 **현재 예외의 traceback까지** 자동으로 남는다 — 어떤 함수·코드 위치를 거쳐 오류가 났는지 그대로 보존된다.

**기록하는 것과 오류를 처리하는 것은 별개다.** `logger.exception()`을 호출한다고 예외가 다시 발생하거나 재시도가 일어나지 않는다. 호출한 곳에 실패를 알리려면 그 뒤에 `raise`를 명시해야 한다.

## LangGraph 노드에 로그 남기기

노드도 결국 Python 함수이므로 앞서 만든 로거를 그대로 쓴다.

```python
def answer(state: LoggingState):
    logger.info("answer 시작")
    try:
        if not state["question"]:
            raise ValueError("질문이 비어 있습니다.")
        response = f"질문을 받았습니다: {state['question']}"
    except ValueError:
        logger.exception("answer 실패")
        raise   # 로깅 후에도 예외는 그대로 호출자에게 전달
    logger.info("answer 완료")
    return {"answer": response}
```

정상 실행이면 `prepare 시작 → prepare 완료 → answer 시작 → answer 완료` 순으로 INFO 로그가 남고, 공백만 입력해 `answer`에서 실패하면 `answer 시작`과 `answer 실패`(traceback 포함)만 남고 `answer 완료`가 빠진다 — 로그만 봐도 어느 노드에서, 어떤 단계까지 실행되다 멈췄는지 알 수 있다. [장애 허용](LangGraph_장애허용.md)에서 재시도·재개를 판단할 때도 이런 노드별 시작/완료/실패 로그가 그 근거 자료가 된다.
