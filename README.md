# AI Agent 엔지니어 부트캠프 TIL

AI Agent 엔지니어 부트캠프에서 배운 내용을 정리하는 저장소입니다.

## 학습 타임라인 (날짜 → 문서)

각 문서를 처음 커밋한 날짜 기준입니다.

| 날짜 | 다룬 문서 |
|------|-----------|
| 2026-07-23 | [Git 명령어 정리](github실습/Git명령어정리.md), [MD 문법 사용 예시 모음](github실습/MarkDownTest.md), [기준선 작성](프로그램방법론/기준선작성.md) |
| 2026-07-24 | [AI와 함께 찾은 나의 강점](Claude실습/나의강점.md) |
| 2026-07-26 | [AI 리터러시 & LLM 애플리케이션 입문](CS지식/LLM_APP입문.md), [프로젝트를 바라보는 방법](프로그램방법론/프로젝트를바라보는방법.md), [기준선 작성 참고](프로그램방법론/기준선작성참고.md), [프로젝트 도구](프로그램방법론/프로젝트도구.md) |
| 2026-07-27 | [n8n](n8n실습/n8n.md), [프롬프트 엔지니어링](CS지식/프롬프트엔지니어링.md), [구글 폼 3개 입력받으면 이메일 보내기](n8n실습/구글폼3개입력받으면이메일보내기.md) |
| 2026-07-28 | [Claude 기본](Claude실습/claude기본.md), [커밋 잘 쓰는 법](github실습/commit잘쓰는법.md), [게임만들기 — Maze Relay](Claude실습/게임만들기/README.md) |
| 2026-07-29 | [API 실습 — 간단 사주 보기](Claude실습/api실습/사주프로그램/사주보기.md), [API 기초](CS지식/API기초.md) |
| 2026-07-30 | [내 자동화 봇 소개](n8n실습/내자동화봇소개.md), [AI Agent란 — 서비스 구조와 실행 환경](CS지식/AIAgent구조.md) |
| 2026-07-31 | [URL 구조](CS지식/URL구조.md), [HTTP 기초](CS지식/HTTP기초.md), [HTTP 상태 코드](CS지식/HTTP상태코드.md) |
| 2026-08-01 | [금융투자봇 — KIS 모의투자 연동 텔레그램 AI 에이전트](n8n실습/금융투자봇/README.md), [아침 자동화 봇 커스터마이징](n8n실습/내자동화봇커스터마이징.md), [미니프로젝트 아이디어 초안](프로그램방법론/미니프로젝트아이디어초안.md) |
| 2026-08-02 | [한국투자증권 Open API 연동 가이드](n8n실습/금융투자봇/KIS_API_연동가이드.md) |
| 2026-08-03 | [소프트웨어 종류](CS지식/소프트웨어종류.md), [컴퓨터 구조](CS지식/컴퓨터구조.md), [웹 서비스 구조](CS지식/웹서비스구조.md), [맛집 추천 서비스 기준선](vercel실습/맛집추천서비스/맛집추천서비스기준선.md), [DB 설계](vercel실습/맛집추천서비스/맛집추천서비스DB설계.md), [화면 설계](vercel실습/맛집추천서비스/맛집추천서비스화면설계.md), [구현 정리](vercel실습/맛집추천서비스/맛집추천서비스구현.md) |
| 2026-08-04 | [웹 디자인 기초](CS지식/웹디자인기초.md), [맛집 추천 서비스 구현 정리 업데이트](vercel실습/맛집추천서비스/맛집추천서비스구현.md) — 디자인 시스템 적용, 네이버/Gemini API 위치 기반 추천 추가, [KIS 모의투자 텔레그램 에이전트 기획서](KIS-Agent-Notes/01_Baseline/01_project_statement.md) — 기준선~실행계획 17개 문서 (KIS-Agent-Notes), [RSS 기초](CS지식/RSS기초.md) |
| 2026-08-05 | [고객VOC분석Agent — VOC 자동 분류·긴급 알림 파이프라인](n8n실습/고객VOC분석Agent/README.md) — Google Form 접수부터 Gemini 분류·중복 방지·검증 안전판·Discord 긴급 알림까지 무인 파이프라인 미니프로젝트 |
| 2026-08-06 | [금융뉴스브리핑Agent — 금융 뉴스 자동 브리핑 시스템](n8n실습/금융뉴스브리핑Agent/README.md) — RSS 수집·중복 차단·금융 키워드 필터·본문 추출·Gemini 요약/중요도 분류를 거쳐 매일 아침 디스코드로 브리핑하는 자동화 미니프로젝트 |
| 2026-08-08 | [왜샀어(WhyBuy) — 근거를 남겨야 완료되는 모의투자 서비스](vercel실습/왜샀어/왜샀어구현.md) — KIS 모의투자 API로 실제 매수·매도 주문을 내되 판단 근거를 강제하는 Next.js 웹 서비스. 초당 1건 레이트리밋 해결, 지정가 주문 도입에 따른 상태 모델 재설계, AI 해석 안전장치, 공유 모의계좌의 자본시장법상 리스크 검토까지 정리 |
| 2026-08-10 | [왜샀어 발표자료](vercel실습/왜샀어/왜샀어_발표.pptx) — 왜샀어(WhyBuy) 프로젝트 발표용 pptx |
| 2026-08-11 | [파이썬 기초](CS지식/파이썬기초/README.md) — 변수·자료형·연산자·입출력·조건문·리스트·반복문 7개 주제 정리 |
| 2026-08-12 | [Docker로 n8n 셀프호스팅하고 Telegram 웹훅 연동하기](n8n실습/Docker로n8n셀프호스팅하기.md) — Windows Home + WSL2 + Docker Desktop 설치 트러블슈팅, ngrok으로 로컬 웹훅 공개, ngrok vs Cloudflare Tunnel 비교, [컨테이너 기반 배포 기초](CS지식/컨테이너배포기초.md) — 이미지·레지스트리·배포 대상(Cloud Run/K8s/VM/PaaS)·Docker Compose 개념 정리, [왜샀어 Docker 배포 전환 기획서](https://github.com/jjh7757/whybuy/blob/master/KIS-Web-Agent-Notes/08_Deploy/01_docker_migration.md) — 서버리스에서 상주 프로세스로 옮겨 KIS 레이트리밋 큐 단일성·체결 확인 스케줄러 한계를 해소하는 이관 계획 (whybuy 저장소) |
| 2026-08-13 | [파이썬 기초](CS지식/파이썬기초/README.md) 문자열·집합과 튜플·딕셔너리·함수·모듈 5개 주제 추가 — 문자열 포매팅과 메서드, 집합 연산과 튜플, 딕셔너리 키-밸류 조작, 함수의 구조와 내장함수, math·random·collections·itertools 표준 모듈 |
| 2026-08-14 | [왜샀어 Docker 배포 전환 작업 로그](vercel실습/왜샀어/Docker배포전환.md) — Vercel에서 네이버클라우드 Micro Server(Docker 셀프호스팅)로 옮기는 실제 작업 기록 시작. 서버 업체 재선정(오라클 홈 리전 이슈로 네이버클라우드 전환), SSH·sshd 트러블슈팅, 스왑·Docker·ufw 구성, 도메인 연결과 Caddy HTTPS 발급, OAuth 리다이렉트 URI 등록까지 |
| 2026-08-15 | [왜샀어 Docker 배포 전환 작업 로그](vercel실습/왜샀어/Docker배포전환.md) 이어서 진행 — 리버스 프록시 뒤에서 로그인 리다이렉트가 컨테이너 자체 hostname으로 새던 버그 추적·수정(Next.js standalone origin 이슈), 반복 재빌드 중 디스크 풀·SSH 연결 불안정 트러블슈팅, 로컬 Docker Desktop 복구. 로그인·조회·레이트리밋·분봉차트·재시작 내구성 검증(T2~T5, T7) 통과, whybuy 저장소에 Docker 배포 코드 반영 |
| 2026-08-16 | [다크패턴 스캐너 — 쇼핑몰 다크패턴 자동 진단 프로토타입](다크패턴스캐너/README.md) — 카운트다운 리셋 탐지(A/B/C 세 조건 재방문 비교)와 체크아웃 단계별 총액 추적을 Playwright로 구현, 정답을 아는 fixture 6종으로 자체 검증(8/8 통과, 오탐 0건). 경쟁 제품(Shopify StoreHQ, 카페24 Sentio5)이 관리자 API 설정값만 보는 것과 달리 실제 렌더링·상호작용을 검증하는 것이 차별점 |
| 2026-08-17 | [다크패턴 스캐너 — 실사이트 검증 및 보류](다크패턴스캐너/README.md) — 무신사·카페24 쇼케이스 브랜드(오롤리데이·쿤달) 등 실사이트 4곳에 스캐너를 돌려 실제 버그 4개(캐러셀 오탐·타이밍, select 직후 클릭 경합, open shadow DOM 위젯 사각지대)를 찾아 고쳤으나 다크패턴은 4연속 미발견. 표본이 "다크패턴이 없을 법한 곳"에 편중된 한계와 "셀러가 이 스캔에 돈을 낼 것인가"라는 미검증 수요 문제를 정리해 프로젝트 보류 결정 ([기획서](다크패턴스캐너/기획서.md) 9장) |
| 2026-08-18 | [파이썬 기초 — 스코프](CS지식/파이썬기초/13_스코프.md) — 함수 내부/외부 변수 접근 범위, LEGB 규칙(Local·Enclosed·Global·Built-in), enclosed 스코프와 중첩 함수, `global` 키워드로 외부 값을 바꾸는 예외 상황과 실무에서 지양해야 하는 이유, 파이썬은 if/for에 block scope가 없다는 점 정리, [알고리즘](CS지식/알고리즘/README.md) — 2차원 배열 인덱싱과 참조 함정, 델타 탐색으로 상하좌우 이웃 확인, 회문 판별 네 가지 방법(슬라이싱·반복·절반 비교·투 포인터), 카운팅·버블·선택 정렬 정리 |
| 2026-08-19 | [파이썬 기초 — 예외 처리](CS지식/파이썬기초/14_예외처리.md) — try/except 기본 구조, 특정·다중 예외 처리, `as`로 예외 객체 참조, else/finally, raise로 예외 강제 발생, 사용자 정의 예외 클래스, [알고리즘 — 큐와 스택](CS지식/알고리즘/05_큐와스택.md) — `collections.deque`가 list보다 양끝 삽입/삭제에 유리한 이유, 올바른 괄호(스택으로 여러 종류 괄호 짝 검사), 다리를 지나는 트럭(큐로 다리 위 상태 시뮬레이션), [알고리즘 — 나선형 배열](CS지식/알고리즘/06_나선형배열.md) — 방향 벡터를 순환시켜 시계방향 나선을 채우고, 범위 이탈과 중복 방문을 함께 체크하는 방법, [requests로 API 호출하기](CS지식/requests실습.md) — GET/POST/PATCH/PUT/DELETE 실습, params·headers 옵션, Timeout·HTTPError·RequestException 예외 처리, [나만의 채용 공고](프로그램방법론/나만의채용공고.md) — AI Agent 엔지니어 실제 채용 공고 5개(원티드랩·넥스트증권·피피에스·스케일아키텍처·모비니티)를 기술스택·자격요건·우대사항 기준으로 뽑아 현재 충족/단기 충족 가능/장기간 필요로 분류 |
| 2026-08-20 | [함수 — key와 람다, 콜스택](CS지식/파이썬기초/11_함수.md) — `max`/`sorted`에 비교 기준 함수를 넘기는 `key` 인자와 람다(익명함수), 함수 호출이 스택처럼 쌓이고(push) 반환되며 빠지는(pop) 콜스택 동작, [환경변수와 .env 관리](CS지식/환경변수관리.md) — `python-dotenv`로 `.env` 읽기, 토큰을 코드에 직접 적지 않는 이유, `.env.example`로 필요한 키만 공유하는 관례, [requests로 API 호출하기](CS지식/requests실습.md) — TMDB API 실전 예제 추가(Bearer 토큰 인증, 함수 내부에서는 raise만 하고 호출부에서 예외 처리, `max(key=...)`로 평점 최고 영화 찾기) |
| 2026-08-21 | [클래스](CS지식/파이썬기초/15_클래스.md) — 인스턴스 변수와 클래스 변수의 공유·가리기(shadowing), 매직 메서드(`__str__`/`__len__`/`__gt__`)로 내장 함수·연산자와 연결하기, `@property`/`setter`로 유효성 검사가 붙은 접근자 만들기, `@classmethod`, 메서드에 데코레이터 적용하기, [클래스 상속](CS지식/파이썬기초/16_클래스상속.md) — 메서드 오버라이딩, `super()`로 부모 생성자·메서드 재사용, 다중 상속, [requests로 API 호출하기](CS지식/requests실습.md) — 공공데이터포털 미세먼지 API 실전 예제 추가(서비스 키 `unquote` 디코딩, 504 에러 재시도 로직, 문자열 결측치(`'-'`) 비교 함정, 응답을 JSON 파일로 캐싱해 재사용하기, 리스트를 딕셔너리로 재구성해 조회 최적화) |
| 2026-08-24 | [추상 클래스와 다형성](CS지식/파이썬기초/17_추상클래스와다형성.md) — 덕타이핑으로 상속 없이도 같은 인터페이스로 여러 객체 다루기, `abc`/`abstractmethod`로 자식이 반드시 구현해야 하는 메서드를 강제해 미구현을 인스턴스 생성 시점에 바로 에러로 잡기, [합성과 의존성 주입](CS지식/파이썬기초/18_합성과의존성주입.md) — 상속(is-a) vs 합성(has-a), 로거·전원 공급 객체를 생성자로 주입해 구현체를 갈아 끼우는 패턴, 게임 캐릭터(직업·무기 합성)와 스마트홈 허브(프로토콜 호환성 체크) 실전 예제, [타입 힌트와 독스트링](CS지식/파이썬기초/19_타입힌트와독스트링.md) — 변수·함수·클래스 타입 힌트, `int \| str` 합집합 타입, 강제성 없는 힌트의 한계, 독스트링과 `__doc__`/`help()` |
| 2026-08-25 | [합성과 의존성 주입](CS지식/파이썬기초/18_합성과의존성주입.md)에 자판기 실전 예제 추가 — 결제 성공/실패 판단을 `Payment` 구현체에 위임, "상품 없음"·"재고 없음"을 사용자 정의 예외로 표현해 발생 지점과 처리 지점 분리, [추가 문법 모음](CS지식/파이썬기초/20_추가문법모음.md) — `*args`/`**kwargs`, 패킹·언패킹, 얕은/깊은 복사, `with`, `__str__` vs `__repr__`, `is` vs `==`, `TypeVar` 제네릭, `Protocol`로 런타임 강제 없이 덕 타이핑에 정적 타입 검사 더하기, 제너레이터(`yield`), [Gemini API 실습](CS지식/Gemini_API실습.md) — Interactions API로 LLM 호출, `input` 세 가지 형태, 대화 맥락(수동 history vs `store=True` 서버 저장·분기), `generation_config`, `ClientError`/`ServerError` 처리, [Gemini 구조화 출력](CS지식/Gemini_구조화출력.md) — Pydantic 모델로 JSON Schema 생성해 응답 형식 강제, `model_validate_json()`으로 파싱·검증 동시에 하기 |
| 2026-08-26 | [Gemini 함수 호출](CS지식/Gemini_함수호출.md) — 모델은 실행 권한이 없고 `function_call`로 요청만 한다는 원칙, 도구 schema 작성, `call_id`로 호출과 결과 짝짓기, 여러 도구 중 모델이 스스로 선택, 반복 호출을 자동 처리하는 Agent loop와 최대 반복 횟수 제한, [Gemini 내장 도구](CS지식/Gemini_내장도구.md) — `code_execution`/`google_search`를 Gemini 서버가 직접 실행하는 방식과 커스텀 Function Calling의 차이, 두 종류를 한 `tools` 목록에 함께 등록하기, [Gemini 스트리밍 응답](CS지식/Gemini_스트리밍.md) — SSE와 제너레이터로 이해하는 스트리밍 원리, `step.delta` 조각을 실시간 출력하며 이어붙여 전체 응답 재구성하기 |
| 2026-08-27 | [Gemini 멀티모달 입력](CS지식/Gemini_멀티모달.md) — 이미지·PDF·음성·동영상을 Base64/Files API/공개 URL로 전달하는 세 가지 방법과 각각이 적합한 상황, `response_format`으로 이미지 생성 요청하기, [비동기 기초](CS지식/파이썬기초/21_비동기기초.md) — 동기/비동기 차이, 이벤트 루프와 코루틴, `async`를 썼다고 자동으로 동시 실행되는 게 아니라는 점, `asyncio.gather()`로 여러 API 요청 동시 처리, Notebook과 `.py` 파일에서 `await` 사용법 차이, [Gemini 비동기 요청](CS지식/Gemini_비동기요청.md) — 비동기가 한 요청의 속도가 아니라 여러 독립 요청의 전체 대기 시간을 줄이는 것이라는 점, `client.aio`로 비동기 클라이언트 만들기, 동시 요청 개수를 제한해야 하는 이유 |
| 2026-08-28 | [예산관리Agent — Gemini Function Calling 개인 예산 관리 Agent](예산관리Agent/README.md) — 구글시트를 저장소로 삼아 거래 등록·검색·수정·삭제와 카테고리별 월 예산 조회를 Gemini Function Calling으로 구현. tool 함수와 호출부의 언패킹 방식 불일치 버그, `additionalProperties: false`로도 못 막는 LLM의 비결정적 인자 추가, 검색 결과 다건 시 되묻게 만드는 system_instruction, `ValueError` 메시지가 Agent를 거쳐 사용자에게 그대로 전달되도록 예외 처리 계층 정리, `strptime`이 0패딩 안 된 날짜도 통과시키는 허점 발견 등 트러블슈팅 정리 |
| 2026-09-01 | [프롬프트 엔지니어링](CS지식/프롬프트엔지니어링.md) 대폭 보강 — 퓨샷 설계 원칙(대표 예시·경계 사례·균형 분포), 역할 부여가 지식이 아니라 관점·우선순위를 바꾸는 효과, 프롬프트로 유도 vs 스키마로 강제하는 출력 형식, XML 태그의 한계(보안 장치 아님), 명시적 단계 분해와 검증 가능한 결과 요청, 프롬프트 체이닝, temperature, 긴 컨텍스트 구조화, 반복 평가 방법론, [LangChain 기초](CS지식/LangChain_기초.md) — ChatModel과 메시지, PromptTemplate/ChatPromptTemplate, LCEL(`\|`)로 체인 연결, Runnable 인터페이스, RunnableLambda로 타입 변환, RunnablePassthrough로 context 주입, [LangChain 실행과 안정성](CS지식/LangChain_실행과안정성.md) — 토큰 모니터링, exponential backoff 재시도와 fallback 모델, 응답 캐싱, `batch`/`stream`과 `asyncio.gather()`의 역할 차이, [LangChain 구조화 출력](CS지식/LangChain_구조화출력.md) — Output Parser 5종 비교, JSON 문법/schema/domain/policy 4단계 검증, `with_structured_output()` vs `PydanticOutputParser`, 실패 원인(provider/파싱/검증)별 재시도·fallback 전략, [LangSmith 기초](CS지식/LangSmith_기초.md) — 환경변수만으로 자동 트레이싱, 태그·메타데이터로 실행 필터링, [LangChain 메모리](CS지식/LangChain_메모리.md) — stateless 호출, `InMemoryChatMessageHistory`로 세션별 관리, `trim_messages()`로 context window 관리, short-term vs long-term memory |
| 2026-09-02 | [LangChain Tool과 기본 Agent](CS지식/LangChain_Tool과Agent.md) — `@tool` 데코레이터로 함수를 Tool로 바꾸기(docstring이 설명, 타입 힌트가 스키마), `bind_tools()`는 실행이 아니라 요청만 만든다는 점, Tool 호출 루프, TMDB 목록·상세 조회를 세션별 메모리와 엮은 실전 Agent, [RAG 기초](CS지식/RAG_기초.md) — Document Loader/Text Splitter로 문서를 청크로 준비하기, `embed_query` vs `embed_documents`, 코사인 유사도로 직접 구현한 유사도 검색, [벡터 DB](CS지식/벡터DB.md) — 일반 DB와 다른 이유(ANN, HNSW/IVF), 메타데이터는 임베딩되지 않고 필터링에만 쓰인다는 점, Chroma로 저장·검색·필터링, 임베딩 모델을 바꾸면 벡터 DB를 재구축해야 하는 이유 |
| 2026-09-03 | [RAG 파이프라인](CS지식/RAG_파이프라인.md) — 검색·포매팅·프롬프트·생성을 `RunnablePassthrough.assign()`과 딕셔너리 병렬 구성 두 가지 문법으로 체인 하나로 조합, retriever를 한 번만 호출해 답변과 출처를 함께 반환하기, 출처 번호도 LLM 생성이라 정확성이 보장되지 않는다는 주의점, [RAG 검색 고도화](CS지식/RAG_검색고도화.md) — 검색 문제는 알고리즘 이전에 문서 추출·청킹 품질부터 점검, MMR로 결과 다양성 확보(`fetch_k`/`lambda_mult`), 형태소 분석기를 붙인 BM25로 정확한 모델명 찾기, Metadata Filter는 관련성이 아니라 검색 범위를 강제하는 용도, EnsembleRetriever의 RRF로 벡터 검색과 BM25 결합, `with_structured_output()`으로 후보를 점수 매겨 재정렬(Re-ranking)하되 후보 본문을 신뢰할 수 없는 입력으로 다뤄야 하는 이유 |
| 2026-09-04 | [RAG 평가](CS지식/RAG_평가.md) — 검색 평가(Hit@k·Precision@k·Recall@k·MRR)와 답변 평가(인용 규칙 검사·RAGAS·LLM-as-Judge)를 분리해서 측정하는 이유, easy/medium/hard를 섞은 평가 데이터셋 설계, Faithfulness·Answer Relevancy 두 점수를 함께 읽는 법, 도메인 채점 기준(정확성·완전성·근거성·출처 정확성)을 직접 정의하는 LLM-as-Judge, File Hit과 Page Hit처럼 정답 단위를 무엇으로 잡을지에 따라 같은 검색 결과도 다르게 평가된다는 점 |
| 2026-09-07 | [RAG 실험 스크립트](CS지식/RAG_실험스크립트.md) — 실험 조건을 config(dataclass)로, 실행 시점 값은 CLI 인자로 분리해 청킹·검색 전략·k·hybrid_weights를 반복 비교하는 구조, golden set과 맞물리게 `source`(경로→파일명)·`page_no`(0→1 시작) 메타데이터를 로드 시점에 정규화해야 지표가 조용히 0이 되지 않는다는 점, 벡터스토어를 전략 수만큼 다시 만들지 않기, 한국어 BM25는 Kiwi 형태소 분석 + 품사 필터로 내용어만 남겨야 조사 차이에 일치가 깨지지 않는다는 점(BM25 최고 성능의 전제), Gemini 무료 티어 RPM 제한(연속 요청 시 5회 이후 429, 약 50초 뒤 복구) 발견과 재시도(지수 백오프)·쿼리 임베딩 캐싱·페이싱 3중 대응, 쿼리 캐싱을 넣은 순간 `latency_ms`가 실행 순서에 오염돼 전략 비교 지표로 무효가 된다는 점, 문항 35개 기준 MRR 차이의 통계적 유의성을 표본 크기로 판단하기, 부분집합 검사에서 공집합이 통과하는 경계를 `bool(citations)`로 막기, 인용 지표가 전부 1.0으로 포화되면 변별력이 없다는 뜻이라는 점, [RAG 실험 스크립트 비교분석](CS지식/RAG_실험스크립트_비교분석.md) — 같은 과제의 참고 구현과 내 구현을 과제 체크리스트(input 15항목·output 6범주) 기준으로 대조, `EnsembleRetriever` 반환값을 `[:k]`로 자르지 않아 Hybrid만 10위까지 훑고 나머지는 5위까지만 훑던 MRR 측정 비대칭 발견(지표 함수는 맞게 구현돼 있었고 틀린 건 비교 조건이었다는 점), 문항별 원자료를 계산해놓고 집계만 저장해 실패 원인 추적이 불가능해진 문제, RRF 융합 후보 풀 깊이(5+5 vs 20+20)가 `hybrid_weights` 스윕 결론에 미치는 영향, 쿼리 캐싱으로 처리량을 얻고 latency 측정 가능성을 잃은 트레이드오프, 단일 프로세스 vs 단계 분리 파이프라인, 규칙 기반 인용 검사 vs RAGAS(`target_answer`를 안 써서 정답성을 잴 수 없었던 설계), SHA-256 해시·`case_id`·`validate_config`·`--dry-run`으로 재현성과 조기 실패를 확보하는 방법 |
| 2026-09-09 | [LangGraph 기초 — 분기·루프·Reducer와 재시도 그래프](CS지식/LangGraph_기초.md) — Chain의 한계와 Chain/Workflow/Agent 스펙트럼, State·Node·Edge 3요소와 Reducer(`add_messages` vs `operator.add`), write→review→재작성 루프 실습에서 정답과 내 구현 비교(전체 이력 누적 vs 최신값만 유지, `attempt`를 반환 dict에 안 넣으면 `KeyError` 나는 함정, if문 vs 프롬프트로 분기 흡수), class로 llm을 갈아끼우는 구조(review는 항상 진짜 llm, write만 교체), 랭체인 내장 `FakeListChatModel`로 재시도 로직 테스트하기, [LangGraph ReAct 에이전트](CS지식/LangGraph_ReAct에이전트.md) — ToolNode·tools_condition이 대신해주는 Tool 호출 반복 처리, Tool은 함수가 아니라 docstring/타입으로 만든 스키마로 노출된다는 점, 저수준(StateGraph 직접 조립) vs 고수준(`create_agent`) 비교, Local File Agent 실습에서 워크스페이스·확장자로 접근 범위를 제한한 이유, [LangGraph 메모리와 상태](CS지식/LangGraph_메모리와상태.md) — Checkpointer(단기, thread_id)와 Store(장기, namespace/key) 역할 구분, `get_state`/`get_state_history`로 State 스냅샷 조회, namespace로 사용자별 데이터를 격리해야 하는 보안 이유, "invoke 한 번 = 상호작용 한 번"이 아니라는 착각 정리, `trim_messages`+`RemoveMessage`로 대화 요약하되 Checkpointer 저장소 원본은 지워지지 않는다는 점 |
| 2026-09-10 | [LangGraph RAG Agent](CS지식/LangGraph_RAG에이전트.md) — Retriever를 `create_retriever_tool`로 Tool화해서 검색 여부를 LLM이 스스로 판단하게 만들기, `document_prompt`/`document_separator`로 metadata·출처 노출과 문서 경계 제어, System Prompt만으로 개방형/제한형(문서 근거만 허용) 두 운영 모드 전환, Checkpointer 결합한 대화형 RAG, [LangGraph 라우팅](CS지식/LangGraph_라우팅.md) — Deterministic/LLM/Semantic/Hybrid Routing 비교, LLM이 만든 confidence를 그대로 신뢰하면 안 되는 이유, Semantic Routing의 대표 문장·threshold는 실험으로 조정할 값이지 과신할 값이 아니라는 점, Flat vs Hierarchical Routing과 routing accuracy·fallback rate·unsafe routing rate 평가 기준, [LangGraph 가드레일](CS지식/LangGraph_가드레일.md) — Input/Output Guardrail 계층 구조, 중요한 규칙은 LLM 판단이 아니라 코드로 강제해야 한다는 원칙, 프롬프트 인젝션 다층 방어, PII 노출 시 마스킹보다 `retry_count` 있는 재생성 루프가 자연스럽다는 점, `input_schema`/`output_schema`로 내부 State와 외부 계약 분리, [LangGraph Reflection과 Evaluator-Optimizer](CS지식/LangGraph_Reflection과EvaluatorOptimizer.md) — 자기 개선 루프 두 가지 비교(자연어 피드백 vs 구조화된 점수), "반복 = 항상 품질 향상"이 아니라는 한계, 좋은 루브릭과 나쁜 루브릭의 차이(측정 가능성), 같은 LLM이 생성·평가를 겸할 때의 자기 평가 편향 |
| 2026-09-11 | [LangGraph 병렬 처리](CS지식/LangGraph_병렬처리.md) — 노드를 나란히 연결하면 자동 병렬 실행되는 Fan-out/Fan-in, `operator.add` reducer로 결과 누적, 완료 순서가 보장 안 되니 식별자로 정렬해야 한다는 점, Voting 패턴(여러 후보 생성 후 최선 선택), 그래프 대신 `batch()`가 더 간단한 경우, [LangGraph Orchestrator-Worker](CS지식/LangGraph_OrchestratorWorker.md) — 고정 Fan-out과 달리 `Send` API로 실행 시점에 동적으로 Worker 수를 정하는 패턴, ReportState(전체 공유) vs WorkerState(작업 하나만), `task_id`로 병렬 완료 순서와 무관하게 재정렬하기, Rate Limiting(RPM/TPM/RPD)과 `max_concurrency`·`asyncio.Semaphore`로 동시 요청 제한하기, [AWS 배포 환경 구축](AWS배포환경/README.md) — `git push` 하나로 빌드·배포가 끝나는 상시 서버를 AWS 단일 구성으로 구축. GitHub OIDC로 장기 액세스 키 없이 인증하고, Actions에서 arm64 빌드 → ECR → SSM Run Command로 EC2에 반영, Caddy가 HTTPS 자동 발급. 서버 사양 선택(오라클 가입 실패·프리티어 제도 변경·EC2 vs Lightsail)부터 [트러블슈팅](AWS배포환경/구축기록.md)(GitHub의 `sub` 클레임이 ID를 포함하도록 바뀌어 AWS 콘솔 마법사가 만든 신뢰 정책과 매칭되지 않던 문제, 배포는 성공했는데 compose 변수 범위 때문에 워크플로가 실패하던 문제)까지 정리 |
| 2026-09-12 | [RAG 앱 배포 기록](AWS배포환경/rag앱배포기록.md) — 전날 만든 AWS 배포 환경에 공공문서 RAG 서비스([rag-web](https://github.com/jjh7757/rag-web))를 처음 올린 기록. 평가 CLI로 있던 RAG 코드에서 서빙에 필요한 부분만 떼어내 FastAPI로 감싸고, 인덱스를 백그라운드에서 구축(기동을 막으면 헬스체크 실패로 502)·fingerprint로 재사용 판단·볼륨 저장하도록 설계. 공개 URL이라 IP별 요청 제한 추가. 배포 절차 7단계 중 막힌 건 ECR 리전 하나뿐이었고, 이미지가 30MB에서 1.5GB로 커지면서 `docker image prune -f`가 태그 달린 이전 버전을 못 지우는 버그가 드러났다. 메모리 실측 667MB와 `free`의 available 읽는 법도 정리 |

## 목차

### Claude실습
- [Claude 기본](Claude실습/claude기본.md) — Chat / Cowork / Code 비교
- [AI와 함께 찾은 나의 강점](Claude실습/나의강점.md) — AI와의 대화로 정리한 나의 강점 3가지
- [게임만들기 — Maze Relay](Claude실습/게임만들기/README.md) — 도트 던전 미로 탈출 게임. 플레이어끼리 Supabase로 메시지를 릴레이하며 죽일지 살릴지 판정하는 비동기 멀티플레이 구조 (원본: [maze-relay](https://github.com/jjh7757/maze-relay))
- [API 실습 — 간단 사주 보기](Claude실습/api실습/사주프로그램/사주보기.md) — 브라우저에서 Gemini API를 직접 호출해 사주를 해석해주는 프론트엔드 실습

### Github 실습
- [Git 명령어 정리](github실습/Git명령어정리.md) — Git 기본 사용 흐름
- [커밋 잘 쓰는 법](github실습/commit잘쓰는법.md)
- [MD 문법 사용 예시 모음](github실습/MarkDownTest.md)

### n8n 실습
- [n8n](n8n실습/n8n.md) — 노코드 자동화 툴 소개
- [구글 폼 3개 입력받으면 이메일 보내기](n8n실습/구글폼3개입력받으면이메일보내기.md)
- [내 자동화 봇 소개](n8n실습/내자동화봇소개.md) — 사주·날씨 기반 오늘의 운세 디스코드 봇
- [금융투자봇 — KIS 모의투자 연동 텔레그램 AI 에이전트](n8n실습/금융투자봇/README.md) — 한국투자증권 모의투자 API를 tool로 쓰는 AI Agent 투자 어드바이저 봇 (금융권 포트폴리오용)
- [한국투자증권 Open API 연동 가이드](n8n실습/금융투자봇/KIS_API_연동가이드.md) — n8n HTTP Request 노드로 KIS 모의투자 API(토큰 발급, 시세·잔고·거래내역 조회) 연동하는 설정값 정리
- [아침 자동화 봇 커스터마이징](n8n실습/내자동화봇커스터마이징.md) — 사주·날씨·맛집 추천 기능을 추가한 봇 커스터마이징
- [고객VOC분석Agent — VOC 자동 분류·긴급 알림 파이프라인](n8n실습/고객VOC분석Agent/README.md) — Google Form 접수 → 중복 방지 → Gemini 분류 → 검증 안전판 → 시트 저장 → Discord 긴급 알림까지 무인 자동화한 미니프로젝트
- [금융뉴스브리핑Agent — 금융 뉴스 자동 브리핑 시스템](n8n실습/금융뉴스브리핑Agent/README.md) — 매일 08:30 RSS 3개 매체 수집 → 중복 차단 → 금융 키워드 필터 → 본문 추출 → Gemini 요약·중요도 분류 → Discord 브리핑 발송까지 무인 자동화한 미니프로젝트
- [Docker로 n8n 셀프호스팅하고 Telegram 웹훅 연동하기](n8n실습/Docker로n8n셀프호스팅하기.md) — Windows Home(WSL2 필수) 환경에서 Docker Desktop 설치 트러블슈팅, n8n 컨테이너 실행, ngrok으로 로컬 웹훅을 공개해 Telegram Trigger 연동

### 프로그램 방법론
- [프로젝트를 바라보는 방법](프로그램방법론/프로젝트를바라보는방법.md) — 프로젝트/프로덕트/운영 구분, WBS, 마일스톤
- [기준선 작성](프로그램방법론/기준선작성.md) — v0.1~v1.0 버전별 프로젝트 기준선(목적·도메인·데이터·이벤트·아키텍처·MVP·완료 기준) 12개 항목
- [기준선 작성 참고](프로그램방법론/기준선작성참고.md) — 도메인·데이터·이벤트·네이밍 컨벤션·아키텍처·방법론(Waterfall/Agile)·MVP 개념 정리
- [프로젝트 도구](프로그램방법론/프로젝트도구.md) — Obsidian, Notion, Jira, GitHub 역할 구분
- [미니프로젝트 아이디어 초안](프로그램방법론/미니프로젝트아이디어초안.md) — 금융투자봇을 리스크 경고·알림·리포트 기능으로 확장한 최종 아이디어
- [나만의 채용 공고](프로그램방법론/나만의채용공고.md) — AI Agent 엔지니어 실제 채용 공고 5개를 기술스택·자격요건·우대사항 기준으로 뽑아 현재 충족/단기 충족 가능/장기간 필요 3단계로 분류

### Vercel 실습
- [맛집 추천 서비스 기준선](vercel실습/맛집추천서비스/맛집추천서비스기준선.md) — 예산 기반 맛집 추천 미니프로젝트 기준선 v0.1
- [맛집 추천 서비스 DB 설계](vercel실습/맛집추천서비스/맛집추천서비스DB설계.md) — `restaurants` 단일 테이블 설계, RLS 정책, 예산 필터링 쿼리
- [맛집 추천 서비스 화면 설계](vercel실습/맛집추천서비스/맛집추천서비스화면설계.md) — 목록/상세/등록 화면 흐름과 DB 필드 매핑
- [맛집 추천 서비스 구현 정리](vercel실습/맛집추천서비스/맛집추천서비스구현.md) — 화면 5개 스크린샷과 구현 내용 정리, 무드보드 기반 디자인 시스템·네이버 지역 검색(NCP)/Gemini API 위치 기반 추천 업데이트 포함 (구현 저장소: [jjh7757/bitebudget](https://github.com/jjh7757/bitebudget))
- [왜샀어(WhyBuy) — 기획과 구현 정리](vercel실습/왜샀어/왜샀어구현.md) — KIS 모의투자 API로 실제 매수·매도 주문을 내되 근거를 강제하는 서비스. 텔레그램 봇([KIS-Agent-Notes](KIS-Agent-Notes/01_Baseline/01_project_statement.md))에서 웹 폼으로 피벗한 배경, KIS 레이트리밋(EGW00201) 해결, 지정가 주문 도입에 따른 주문 상태 모델 재설계, AI 안전장치, 공유 모의계좌의 자본시장법상 리스크 검토 (구현 저장소: [jjh7757/whybuy](https://github.com/jjh7757/whybuy))

### AWS 배포환경
- [AWS 배포 환경 구축 계획](AWS배포환경/README.md) — 만든 걸 바로 올릴 수 있는 상시 배포 서버. 서버에서 빌드하지 않고, GitHub에 장기 키를 두지 않고, 포트 22를 열지 않는 구조. 비용·가드레일·단계별 체크리스트
- [구축 기록](AWS배포환경/구축기록.md) — 서버 선택 의사결정(네이버 1GB 한계 → 오라클 가입 실패 → 프리티어 제도 변경 확인 → EC2 확정)과 트러블슈팅 2건(OIDC `sub` 클레임의 ID 형식, `deploy-app`의 compose 변수 범위)
- 단계별 절차 — [0. 계정과 가드레일](AWS배포환경/00_계정설정.md) · [1. 네트워크와 인스턴스](AWS배포환경/01_인스턴스생성.md) · [2. 서버 초기 세팅](AWS배포환경/02_서버세팅.md) · [3. 배포 파이프라인](AWS배포환경/03_배포파이프라인.md) · [4. 도메인과 HTTPS](AWS배포환경/04_도메인과HTTPS.md)
- [새 앱을 올릴 때 해야 할 일](AWS배포환경/새앱배포절차.md) — 환경이 갖춰진 뒤 프로젝트 하나를 올릴 때마다 밟는 7단계(ECR·IAM 신뢰 정책·저장소·서버 compose·DNS·Caddy·push)와 체크리스트. 포트를 세 군데서 맞춰야 한다는 점, arm64 빌드, RAM 2GB에서 앱 2~3개가 한계라는 실질 제약, 증상별 확인 지점까지 정리
- [RAG 앱 배포 기록](AWS배포환경/rag앱배포기록.md) — 이 환경에 앱을 처음 올린 기록. 평가 스크립트를 서비스로 옮기며 정한 것(인덱스 백그라운드 구축·볼륨 재사용·질의 직렬화·요청 제한), 작은 앱으로만 검증한 파이프라인이 1.5GB 이미지에서 처음 깨진 지점, 메모리 실측치
- [재사용 템플릿](AWS배포환경/templates/) — 서버 초기 세팅 스크립트, Caddy·앱 compose, Actions 워크플로, IAM 정책 3종 (검증용 테스트 앱 저장소: [jjh7757/deploy-test](https://github.com/jjh7757/deploy-test))

### 다크패턴스캐너 (보류)
- [다크패턴 스캐너 — 쇼핑몰 다크패턴 자동 진단 프로토타입](다크패턴스캐너/README.md) — 카운트다운 리셋 탐지·체크아웃 단계별 총액 추적을 Playwright로 구현, fixture 6종 자체 검증(8/8) 후 실사이트 4곳 검증까지 마쳤으나 다크패턴 미발견으로 보류. [기획서](다크패턴스캐너/기획서.md)에 시장 근거·경쟁 조사·실사이트 검증 결과·보류 사유 전부 정리

### 예산관리Agent
- [예산관리Agent — Gemini Function Calling 개인 예산 관리 Agent](예산관리Agent/README.md) — 자연어로 수입/지출을 기록하고 예산을 관리하는 CLI 에이전트. 구글시트(gspread)를 저장소로 쓰고, Gemini Function Calling으로 거래 등록·검색·수정·삭제·예산 조회를 tool로 노출. 8가지 트러블슈팅(언패킹 방식 불일치, 스키마 제약의 한계, 검색 다건 시 되묻기, 예외 메시지 전달, 날짜 검증 허점, 빈 행 방어 등) 정리

### KIS-Agent-Notes (KIS 모의투자 텔레그램 에이전트 기획)
[금융투자봇](n8n실습/금융투자봇/README.md) 아이디어를 5일 개인 프로젝트로 구체화한 기획서. [기준선 작성](프로그램방법론/기준선작성.md)의 12개 항목 템플릿을 그대로 적용해 기준선부터 실행계획까지 정리.

- **01_Baseline** — [프로젝트 한 문장](KIS-Agent-Notes/01_Baseline/01_project_statement.md)(성공 기준을 "수익"이 아닌 "판단 근거 설명 가능"으로 잡은 이유, 확인한 사실 7개·미검증 가정 5개), [프로젝트 기준선](KIS-Agent-Notes/01_Baseline/02_project_baseline.md)(목적·도메인·데이터·이벤트·아키텍처·범위·완료 기준 12개 항목)
- **02_Domain** — [도메인 요소](KIS-Agent-Notes/02_Domain/01_domain_elements.md), [사용자 역할](KIS-Agent-Notes/02_Domain/02_user_roles.md), [정상·예외 업무 흐름](KIS-Agent-Notes/02_Domain/03_workflow.md)(정상 흐름 4개·예외 흐름 11개)
- **03_Data_Event** — [데이터 구조 초안](KIS-Agent-Notes/03_Data_Event/01_data_structure.md), [데이터 소스](KIS-Agent-Notes/03_Data_Event/02_data_sources.md), [이벤트 카탈로그](KIS-Agent-Notes/03_Data_Event/03_event_catalog.md)(과거형 snake_case 도메인 이벤트 7개), [용어와 네이밍 컨벤션](KIS-Agent-Notes/03_Data_Event/04_naming_convention.md)
- **04_Architecture** — [데이터 흐름](KIS-Agent-Notes/04_Architecture/01_data_flow.md), [아키텍처](KIS-Agent-Notes/04_Architecture/02_architecture.md)(텔레그램 → n8n 메인 워크플로우 + 서브 워크플로우 4개 → KIS 모의투자 Open API, 비용 낮은 순 검증)
- **05_Scope** — [MVP 범위와 기능 우선순위](KIS-Agent-Notes/05_Scope/01_mvp_scope.md), [완료 기준과 체크리스트](KIS-Agent-Notes/05_Scope/02_definition_of_done.md)
- **06_WBS** — [WBS — 개발 작업 분해](KIS-Agent-Notes/06_WBS/01_wbs.md), [5일 마일스톤과 위험](KIS-Agent-Notes/06_WBS/02_milestones.md)(2026-08-05~09 개발, 08-10 발표)
- **07_GitHub** — [GitHub README 초안](KIS-Agent-Notes/07_GitHub/01_readme_draft.md), [2분 발표자료 초안](KIS-Agent-Notes/07_GitHub/02_presentation.md)

### CS지식
- [AI 리터러시 & LLM 애플리케이션 입문](CS지식/LLM_APP입문.md)
- [프롬프트 엔지니어링](CS지식/프롬프트엔지니어링.md) — 좋은 프롬프트 4요소, 하네스/컨텍스트 엔지니어링, Claude Code 스킬 추가하는 방법, CoT·ReAct·Tree-of-Thought, 퓨샷 설계 원칙, 역할 부여, 출력 형식 지정, XML 태그, 프롬프트 체이닝, temperature, 긴 컨텍스트 처리, 프롬프트 반복 평가
- [URL 구조](CS지식/URL구조.md) — scheme/authority/path/query/fragment 등 URL 구성 요소 정리
- [HTTP 기초](CS지식/HTTP기초.md) — 요청/응답 구조, 메서드, 상태 코드, 무상태 특징 정리
- [HTTP 상태 코드](CS지식/HTTP상태코드.md) — 1XX~5XX 분류와 리다이렉션 개념 정리
- [API 기초](CS지식/API기초.md) — API 개념, REST API, API 키/인증 정리
- [AI Agent란 — 서비스 구조와 실행 환경](CS지식/AIAgent구조.md) — Client/Agent/Server/DB/Cloud 구조와 클라우드가 필요한 이유
- [소프트웨어 종류](CS지식/소프트웨어종류.md) — 웹/모바일/데스크탑 분류와 FE·BE, Android·iOS, 크로스플랫폼(Flutter, React Native) 정리
- [컴퓨터 구조](CS지식/컴퓨터구조.md) — CPU·MB·RAM·SSD/HDD 하드웨어 구성과 프로그램·프로세스·스레드 관계 정리
- [웹 서비스 구조](CS지식/웹서비스구조.md) — Client-Server(FE/BE) 구조, HTTP(요청/응답)와 API 통신 정리
- [웹 디자인 기초](CS지식/웹디자인기초.md) — 화면 설계 전 방향을 잡는 무드보드(Pinterest 활용법·AI로 디자인 시스템/프로토타입 뽑는 프롬프트 예시 포함), 미디어 쿼리·뷰포트 기반 반응형 웹과 모바일 퍼스트 전략 비교
- [RSS 기초](CS지식/RSS기초.md) — RSS 동작 방식과 예시 구조, 알고리즘 없이 구독하는 장점, 웹훅과의 pull/push 차이
- [파이썬 기초](CS지식/파이썬기초/README.md) — 변수·자료형·연산자·입출력·조건문·리스트·반복문·문자열·집합과 튜플·딕셔너리·함수·모듈·스코프·예외 처리·클래스·클래스 상속·추상 클래스와 다형성·합성과 의존성 주입·타입 힌트와 독스트링·추가 문법 모음·비동기 기초 21개 주제 정리
- [컨테이너 기반 배포 기초](CS지식/컨테이너배포기초.md) — 컨테이너 vs VM, Dockerfile·이미지·레지스트리 흐름, 배포 대상(관리형 컨테이너 서비스/쿠버네티스/VM/PaaS) 비교, Docker Compose
- [알고리즘](CS지식/알고리즘/README.md) — 2차원 배열과 참조 함정, 델타 탐색으로 상하좌우 이웃 확인, 회문 판별 네 가지 방법, 카운팅·버블·선택 정렬, 큐와 스택(deque), 나선형 배열 6개 주제 정리
- [requests로 API 호출하기](CS지식/requests실습.md) — GET/POST/PATCH/PUT/DELETE 메서드별 사용법, params·headers 옵션, Timeout·HTTPError 예외 처리, TMDB 인증 API·공공데이터 미세먼지 API 실전 예제
- [환경변수와 .env 관리](CS지식/환경변수관리.md) — `python-dotenv`로 `.env` 읽기, `.env`를 커밋하지 않고 `.env.example`만 공유하는 이유
- [Gemini API 실습](CS지식/Gemini_API실습.md) — Interactions API 기본 흐름, `input`의 문자열/Content 배열/Step 배열, `system_instruction`, 수동 history vs `store=True`+`previous_interaction_id` 대화 이어가기·분기, `generation_config`, `ClientError`/`ServerError` 처리
- [Gemini 구조화 출력](CS지식/Gemini_구조화출력.md) — Pydantic 모델로 JSON Schema 생성, `response_format`으로 응답 형식 강제, `model_validate_json()`으로 파싱과 검증 함께 하기
- [Gemini 함수 호출](CS지식/Gemini_함수호출.md) — 도구 schema 정의, `function_call`/`function_result` 왕복, 여러 도구 중 모델이 스스로 선택, 반복 호출을 처리하는 Agent loop
- [Gemini 내장 도구](CS지식/Gemini_내장도구.md) — `code_execution`/`google_search`를 Gemini 서버가 직접 실행, 커스텀 함수와 함께 등록해 쓰기
- [Gemini 스트리밍 응답](CS지식/Gemini_스트리밍.md) — SSE와 제너레이터로 이해하는 스트리밍 원리, `step.delta` 조각을 모아 전체 응답 재구성하기
- [Gemini 멀티모달 입력](CS지식/Gemini_멀티모달.md) — 이미지·PDF·음성·동영상을 Base64/Files API/공개 URL로 전달, 이미지 생성
- [Gemini 비동기 요청](CS지식/Gemini_비동기요청.md) — `client.aio`로 비동기 클라이언트 만들기, 독립적인 여러 LLM 요청을 `asyncio.gather()`로 동시 처리, 동시 요청 개수 제한 필요성
- [LangChain 기초](CS지식/LangChain_기초.md) — LangChain 생태계, ChatModel과 메시지, PromptTemplate/ChatPromptTemplate, LCEL(`|`)과 Runnable, RunnableLambda·RunnablePassthrough
- [LangChain 실행과 안정성](CS지식/LangChain_실행과안정성.md) — 토큰 모니터링, `max_retries`/`with_fallbacks()`, LLM 응답 캐싱, `invoke`/`batch`/`stream`과 `asyncio.gather()`의 차이
- [LangChain 구조화 출력](CS지식/LangChain_구조화출력.md) — Output Parser 종류 비교, JSON 4단계 검증, `with_structured_output()` vs `PydanticOutputParser`, 실패 원인별 재시도·fallback
- [LangSmith 기초](CS지식/LangSmith_기초.md) — 환경변수만으로 자동 트레이싱, 태그·메타데이터로 실행 구분, 선택적 추적
- [LangChain 메모리](CS지식/LangChain_메모리.md) — stateless 호출과 수동 히스토리, `InMemoryChatMessageHistory`, `trim_messages()`로 context window 관리, short-term vs long-term memory
- [LangChain Tool과 기본 Agent](CS지식/LangChain_Tool과Agent.md) — `@tool` 데코레이터, `bind_tools()`, Tool 호출 루프, TMDB 영화 조회 Agent 실전 예제
- [RAG 기초](CS지식/RAG_기초.md) — Document Loader, Text Splitter(청크 크기·overlap), 임베딩(`embed_query`/`embed_documents`), 코사인 유사도
- [벡터 DB](CS지식/벡터DB.md) — ANN(HNSW/IVF), 메타데이터 필터링, Chroma 실습(저장·검색·Retriever), 임베딩 모델 변경 시 재구축 필요성
- [RAG 파이프라인](CS지식/RAG_파이프라인.md) — 검색·포매팅·프롬프트·생성을 `RunnablePassthrough.assign()`/딕셔너리 병렬 구성으로 체인 하나로 엮기, Inline Citation/Source List로 출처 표시
- [RAG 검색 고도화](CS지식/RAG_검색고도화.md) — MMR로 결과 다양성 확보, BM25로 정확한 키워드 검색, Metadata Filter로 검색 범위 강제, Hybrid Search(RRF), LLM 기반 Re-ranking
- [RAG 평가](CS지식/RAG_평가.md) — 검색 평가(Hit@k/Precision@k/Recall@k/MRR)와 답변 평가(인용 검사/RAGAS/LLM-as-Judge) 분리, Faithfulness·Answer Relevancy 조합 해석, 도메인 특화 LLM-as-Judge 설계, File Hit vs Page Hit
- [RAG 실험 스크립트](CS지식/RAG_실험스크립트.md) — config/CLI 분리로 청킹·검색 전략·k·hybrid_weights 반복 비교, golden set 대조를 위한 메타데이터 정규화(`source`/`page_no`), 한국어 BM25의 Kiwi 토크나이저 + 품사 필터, Gemini 무료 티어 RPM 제한 실측(연속 요청 5회 이후 429)과 재시도·쿼리 임베딩 캐싱·페이싱 대응, 캐싱이 `latency_ms`를 비교 불가능하게 만드는 트레이드오프, 표본 크기 대비 MRR 차이의 통계적 유의성 판단, 포화된(전부 1.0) 지표는 변별력이 없다는 점
- [RAG 실험 스크립트 비교분석](CS지식/RAG_실험스크립트_비교분석.md) — 같은 과제의 참고 구현과 input(15항목)·output(6범주) 목록 대조, `EnsembleRetriever`를 `[:k]`로 자르지 않아 생긴 Hybrid MRR 측정 비대칭, 문항별 원자료 보존과 실패 분석(`retrieval_misses.jsonl`), RRF 융합 후보 풀 깊이, 단계 분리 파이프라인, 규칙 기반 인용 검사 vs RAGAS, `run.json` 해시·`case_id`·`validate_config`·`--dry-run`으로 확보하는 재현성
- [LangGraph 기초](CS지식/LangGraph_기초.md) — Chain/Workflow/Agent 스펙트럼, State·Node·Edge, Reducer(`add_messages`/`operator.add`), 재작성 루프 실습에서 정답과 내 구현 비교, class로 llm 갈아끼우기, 랭체인 내장 `FakeListChatModel`로 테스트하기
- [LangGraph ReAct 에이전트](CS지식/LangGraph_ReAct에이전트.md) — `ToolNode`/`tools_condition`으로 Tool 호출 반복 자동화, Tool 스키마는 docstring이 결정한다는 점, 저수준 조립 vs `create_agent()`, Local File Agent 실습(워크스페이스·확장자 제한)
- [LangGraph 메모리와 상태](CS지식/LangGraph_메모리와상태.md) — Checkpointer(단기, thread_id) vs Store(장기, namespace/key) 구분, `get_state`/`get_state_history`, 사용자별 namespace 격리, `trim_messages`+`RemoveMessage`로 대화 요약하기
- [LangGraph RAG Agent](CS지식/LangGraph_RAG에이전트.md) — Retriever를 `create_retriever_tool`로 Tool화, `document_prompt`/`document_separator`, 개방형/제한형 System Prompt, Checkpointer 결합한 대화형 RAG
- [LangGraph 라우팅](CS지식/LangGraph_라우팅.md) — Deterministic/LLM/Semantic/Hybrid Routing, Flat vs Hierarchical Routing, routing accuracy·fallback rate·unsafe routing rate 평가 기준
- [LangGraph 가드레일](CS지식/LangGraph_가드레일.md) — Input/Output Guardrail 계층, 프롬프트 인젝션 다층 방어, PII 재생성 루프, `input_schema`/`output_schema`로 내부 State 숨기기
- [LangGraph Reflection과 Evaluator-Optimizer](CS지식/LangGraph_Reflection과EvaluatorOptimizer.md) — 자연어 피드백 루프 vs 구조화된 점수 루프, 루브릭 설계, 자기 평가 편향
- [LangGraph 병렬 처리](CS지식/LangGraph_병렬처리.md) — Fan-out/Fan-in, `operator.add` reducer, 결과 순서 정렬, Voting 패턴, 그래프 대신 `batch()` 쓰는 기준
- [LangGraph Orchestrator-Worker](CS지식/LangGraph_OrchestratorWorker.md) — `Send` API로 실행 시점에 Worker 수를 동적으로 정하기, ReportState vs WorkerState, `task_id` 재정렬, Rate Limiting과 `max_concurrency`
